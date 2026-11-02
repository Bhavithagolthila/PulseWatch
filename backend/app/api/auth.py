import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..services.auth import auth_configured, check_credentials, create_token, require_user

logger = logging.getLogger("pulsewatch.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginIn):
    if not auth_configured():
        raise HTTPException(503, "Login is not set up. Set AUTH_USERNAME and AUTH_PASSWORD in backend/.env and restart.")
    if not check_credentials(payload.username, payload.password):
        logger.warning("Failed login attempt")
        raise HTTPException(401, "Incorrect username or password.")
    token, expires = create_token(payload.username)
    return {"access_token": token, "token_type": "bearer", "expires_at": expires}


@router.get("/me")
def me(user: str = Depends(require_user)):
    return {"username": user}
