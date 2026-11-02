"""Email alerts when a monitor changes state (goes down, degrades, recovers)."""
import logging
import smtplib
import ssl
import threading
from email.message import EmailMessage

from ..config import settings

logger = logging.getLogger("pulsewatch.alerts")

HEALTHY, DEGRADED, DOWN = "HEALTHY", "DEGRADED", "DOWN"


class EmailNotConfigured(RuntimeError):
    pass


def email_configured() -> bool:
    return bool(settings.smtp_host and settings.alert_email_to and (settings.alert_email_from or settings.smtp_username))


def detect_event(previous: str | None, current: str) -> str | None:
    """Return "down", "degraded", "recovered", or None when nothing worth emailing happened.

    A first-ever check that is healthy is silent; a first-ever bad check does alert.
    """
    if previous == current:
        return None
    if current == DOWN:
        return "down"
    if current == DEGRADED:
        return "degraded"
    if current == HEALTHY and previous in (DOWN, DEGRADED):
        return "recovered"
    return None


def build_message(event: str, name: str, url: str, status: str, http_status=None, latency_ms=None, error=None) -> tuple[str, str]:
    subjects = {
        "down": f"[PulseWatch] DOWN: {name}",
        "degraded": f"[PulseWatch] DEGRADED: {name}",
        "recovered": f"[PulseWatch] Recovered: {name}",
    }
    lines = [f"Monitor: {name}", f"URL: {url}", f"Status: {status}"]
    if http_status is not None:
        lines.append(f"HTTP status: {http_status}")
    if latency_ms is not None:
        lines.append(f"Response time: {latency_ms} ms")
    if error:
        lines.append(f"Error: {error}")
    return subjects[event], "\n".join(lines)


def send_email(subject: str, body: str) -> None:
    """Send one email synchronously. Raises EmailNotConfigured or an smtplib/OS error."""
    if not email_configured():
        raise EmailNotConfigured("Email is not set up. Set SMTP_HOST and ALERT_EMAIL_TO in backend/.env and restart.")
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.alert_email_from or settings.smtp_username
    message["To"] = settings.alert_email_to
    message.set_content(body)
    security = settings.smtp_security.lower()
    if security == "ssl":
        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15, context=ssl.create_default_context())
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
    with server:
        if security == "starttls":
            server.starttls(context=ssl.create_default_context())
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)


def _send_quietly(subject: str, body: str) -> None:
    try:
        send_email(subject, body)
        logger.info("Alert email sent: %s", subject)
    except Exception:
        logger.exception("Could not send alert email: %s", subject)


def notify_status_change(previous: str | None, monitor, result) -> None:
    """Called after a check is saved. Sends in a background thread so SMTP never slows checks."""
    event = detect_event(previous, result.status)
    if event is None or not email_configured():
        return
    subject, body = build_message(
        event, monitor.name, monitor.url, result.status, result.http_status_code, result.response_time_ms, result.error_message
    )
    threading.Thread(target=_send_quietly, args=(subject, body), daemon=True).start()
