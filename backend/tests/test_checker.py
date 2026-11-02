import asyncio
from unittest.mock import patch

import httpx

from app.config import settings
from app.services.checker import classify, run_check
from app.services.security import UnresolvableHost, UnsafeTarget


def check(handler, url="https://example.com"):
    """Run run_check against a fake server (no network) with URL validation switched off."""
    with patch("app.services.checker.validate_public_url"):
        return asyncio.run(run_check(url, transport=httpx.MockTransport(handler)))


def test_classify_rules():
    assert classify(200, 50) == "HEALTHY"
    assert classify(301, 50) == "HEALTHY"
    assert classify(404, 50) == "DEGRADED"
    assert classify(503, 50) == "DEGRADED"
    assert classify(200, settings.latency_threshold_ms + 1) == "DEGRADED"
    assert classify(200, settings.latency_threshold_ms) == "HEALTHY"  # "at or below" is healthy
    assert classify(200, 50, oversized=True) == "DEGRADED"


def test_healthy_response():
    result = check(lambda request: httpx.Response(200, content=b"ok"))
    assert result.status == "HEALTHY"
    assert result.http_status_code == 200
    assert result.response_time_ms is not None and result.error_message is None


def test_http_error_is_degraded_not_down():
    result = check(lambda request: httpx.Response(500))
    assert (result.status, result.http_status_code) == ("DEGRADED", 500)


def test_oversized_body_is_degraded():
    body = b"x" * (settings.max_response_bytes + 1000)
    result = check(lambda request: httpx.Response(200, content=body))
    assert result.status == "DEGRADED" and "size limit" in result.error_message


def test_redirects_are_not_followed():
    result = check(lambda request: httpx.Response(302, headers={"location": "http://127.0.0.1/"}))
    assert result.http_status_code == 302  # we report the 302 instead of following it


def test_timeout_is_down_without_latency():
    def handler(request):
        raise httpx.ConnectTimeout("slow", request=request)

    result = check(handler)
    assert result.status == "DOWN"
    assert result.response_time_ms is None  # timeouts must not pollute average latency
    assert result.http_status_code is None


def test_connection_failure_is_down():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    assert check(handler).status == "DOWN"


def test_unresolvable_host_is_down():
    with patch("app.services.checker.validate_public_url", side_effect=UnresolvableHost("The hostname could not be resolved.")):
        result = asyncio.run(run_check("https://gone.example.com"))
    assert result.status == "DOWN" and "resolved" in result.error_message


def test_blocked_destination_is_never_requested():
    called = []

    def handler(request):
        called.append(request)
        return httpx.Response(200)

    with patch("app.services.checker.validate_public_url", side_effect=UnsafeTarget("Local and internal hostnames are not allowed.")):
        result = asyncio.run(run_check("http://localhost", transport=httpx.MockTransport(handler)))
    assert result.status == "DOWN" and result.error_message.startswith("Blocked:")
    assert called == []
