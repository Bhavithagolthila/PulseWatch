import asyncio
import logging

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..services.alerts import EmailNotConfigured, email_configured, send_email

logger = logging.getLogger("pulsewatch.alerts")
router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("/config")
def alert_config():
    """Never returns the SMTP password."""
    return {"configured": email_configured(), "recipient": settings.alert_email_to or None}


@router.post("/test")
async def send_test_email():
    try:
        await asyncio.to_thread(
            send_email,
            "[PulseWatch] Test email",
            "This is a test email from PulseWatch. If you can read this, alerts are working.",
        )
    except EmailNotConfigured as exc:
        raise HTTPException(503, str(exc))
    except Exception as exc:
        logger.exception("Test email failed")
        raise HTTPException(502, f"Could not send email: {type(exc).__name__}: {exc}")
    return {"sent_to": settings.alert_email_to}
