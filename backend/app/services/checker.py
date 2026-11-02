"""Performs one HTTP health check. No database code lives here, so it is easy to test."""
import asyncio
import time
from dataclasses import dataclass

import httpx

from ..config import settings
from .security import UnresolvableHost, UnsafeTarget, validate_public_url

HEALTHY, DEGRADED, DOWN = "HEALTHY", "DEGRADED", "DOWN"


@dataclass
class CheckResult:
    status: str
    http_status_code: int | None = None
    response_time_ms: float | None = None  # None when no HTTP response was received
    error_message: str | None = None


def classify(http_status_code: int, response_time_ms: float, oversized: bool = False) -> str:
    """HEALTHY: 2xx/3xx and fast. DEGRADED: 4xx/5xx, slow, or too large."""
    if oversized or http_status_code >= 400 or response_time_ms > settings.latency_threshold_ms:
        return DEGRADED
    return HEALTHY


async def run_check(url: str, transport: httpx.AsyncBaseTransport | None = None) -> CheckResult:
    """GET the URL once and describe the outcome. Never raises for network problems.

    `transport` exists so tests can use httpx.MockTransport instead of the real network.
    """
    try:
        # getaddrinfo blocks, so run it in a worker thread instead of freezing the event loop.
        await asyncio.to_thread(validate_public_url, url)
    except UnresolvableHost as exc:
        return CheckResult(DOWN, error_message=str(exc))
    except UnsafeTarget as exc:
        return CheckResult(DOWN, error_message=f"Blocked: {exc}")

    # Start the clock after validation so latency measures the endpoint, not our DNS check.
    started = time.perf_counter()
    code = None
    response_ms = None
    oversized = False
    try:
        timeout = httpx.Timeout(settings.request_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, transport=transport) as client:
            async with client.stream("GET", url, headers={"User-Agent": "PulseWatch/1.0"}) as response:
                code = response.status_code
                # Time until the response headers arrived (time-to-first-byte).
                response_ms = round((time.perf_counter() - started) * 1000, 2)
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > settings.max_response_bytes:
                        oversized = True
                        break
    except httpx.TimeoutException:
        return CheckResult(DOWN, error_message="Request timed out.")
    except httpx.ConnectError:
        return CheckResult(DOWN, error_message="Could not connect to the host.")
    except httpx.RequestError as exc:
        return CheckResult(DOWN, error_message=f"Request failed: {type(exc).__name__}")
    except Exception as exc:  # e.g. httpx.InvalidURL: record it instead of crashing the caller
        return CheckResult(DOWN, error_message=f"Unexpected error: {type(exc).__name__}")

    error = "Response exceeded the configured size limit." if oversized else None
    return CheckResult(classify(code, response_ms, oversized), code, response_ms, error)
