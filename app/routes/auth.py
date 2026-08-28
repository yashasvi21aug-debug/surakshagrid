from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from app.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


class OfficerLoginRequest(BaseModel):
    badge_id: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=256)


class OfficerPrincipal(BaseModel):
    badge_id: str
    role: str
    demo: bool = False


def _create_access_token(*, badge_id: str, role: str, demo: bool = False) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    claims = {
        "sub": badge_id,
        "role": role,
        "demo": demo,
        "iat": now,
        "exp": expires,
    }
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _token_response(token: str, role: str) -> dict[str, str]:
    return {"access_token": token, "token_type": "bearer", "role": role}


@router.post("/login")
async def login(payload: OfficerLoginRequest) -> dict[str, str]:
    if payload.badge_id != "3492" or not settings.OFFICER_3492_PASSWORD_HASH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid badge credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        valid_password = pwd_context.verify(payload.password, settings.OFFICER_3492_PASSWORD_HASH)
    except (ValueError, TypeError):
        valid_password = False
    if not valid_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid badge credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _token_response(_create_access_token(badge_id="3492", role="COMMANDER"), "COMMANDER")


@router.post("/demo-bypass")
async def demo_bypass() -> dict[str, str]:
    token = _create_access_token(badge_id="3492", role="COMMANDER", demo=True)
    return _token_response(token, "COMMANDER")


async def get_current_officer(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> OfficerPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims: dict[str, Any] = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "role", "exp"]},
        )
        return OfficerPrincipal(badge_id=str(claims["sub"]), role=str(claims["role"]), demo=bool(claims.get("demo", False)))
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError, TypeError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


def require_role(*allowed_roles: str):
    async def dependency(officer: Annotated[OfficerPrincipal, Depends(get_current_officer)]) -> OfficerPrincipal:
        if officer.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient officer role")
        return officer

    return dependency
