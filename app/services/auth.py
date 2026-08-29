from __future__ import annotations

import datetime
import logging
from typing import Any

import jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

SECRET_KEY = "surakshagrid_bharat_shakti_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash plain password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(
    data: dict[str, Any],
    expires_delta: datetime.timedelta | None = None,
) -> str:
    """Create signed JWT bearer token with expiration payload."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate JWT bearer token signature and expiration."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def issue_demo_token_credentials() -> dict[str, Any]:
    """Issue instant evaluation JWT bearer credentials for live review mode."""
    payload = {
        "sub": "NDRF_DEMO_OFFICER",
        "officer_id": "NDRF_DEMO_OFFICER",
        "badge_id": "NDRF-3492",
        "role": "COMMANDER",
    }
    token = create_access_token(payload)
    return {
        "access_token": token,
        "token_type": "bearer",
        "officer_id": "NDRF_DEMO_OFFICER",
        "badge_id": "NDRF-3492",
        "role": "COMMANDER",
        "expires_in_hours": 24,
    }
