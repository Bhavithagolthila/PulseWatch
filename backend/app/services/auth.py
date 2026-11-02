"""Single-owner login with signed, expiring tokens (standard library only).

The username/password live in backend/.env. A token is `base64(payload).signature` where the
signature is an HMAC-SHA256 of the payload with SECRET_KEY, so it cannot be forged or extended.
"""
import base64
import hashlib
import hmac
import json
import logging
import secrets
import time

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import settings

logger = logging.getLogger("pulsewatch.auth")
bearer = HTTPBearer(auto_error=False)

# Used when SECRET_KEY is not configured: valid until the process restarts.
_ephemeral_key = secrets.token_hex(32)


def _key() -> bytes:
    return (settings.secret_key or _ephemeral_key).encode()


def auth_configured() -> bool:
    return bool(settings.auth_username and settings.auth_password)


def check_credentials(username: str, password: str) -> bool:
    """Constant-time comparison; both fields are always compared so timing leaks nothing."""
    if not auth_configured():
        return False
    user_ok = hmac.compare_digest(username.encode(), settings.auth_username.encode())
    pass_ok = hmac.compare_digest(password.encode(), settings.auth_password.encode())
    return user_ok and pass_ok


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str) -> str:
    return _b64(hmac.new(_key(), payload.encode(), hashlib.sha256).digest())


def create_token(username: str, now: float | None = None) -> tuple[str, int]:
    issued = int(now if now is not None else time.time())
    expires = issued + settings.token_ttl_hours * 3600
    payload = _b64(json.dumps({"sub": username, "exp": expires}).encode())
    return f"{payload}.{_sign(payload)}", expires


def verify_token(token: str, now: float | None = None) -> str | None:
    """Return the username for a valid, unexpired token, otherwise None."""
    try:
        payload, signature = token.split(".", 1)
        if not hmac.compare_digest(signature, _sign(payload)):
            return None
        data = json.loads(_unb64(payload))
        if data["exp"] < (now if now is not None else time.time()):
            return None
        if not hmac.compare_digest(str(data["sub"]).encode(), settings.auth_username.encode()):
            return None
        return data["sub"]
    except Exception:
        return None


def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    """FastAPI dependency: 401 unless the request carries a valid token."""
    user = verify_token(credentials.credentials) if credentials else None
    if not user:
        raise HTTPException(401, "Not logged in.", headers={"WWW-Authenticate": "Bearer"})
    return user
