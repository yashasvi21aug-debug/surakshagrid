from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Union
import jwt
import datetime

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)

SECRET_KEY = "surakshagrid_bharat_shakti_secret_key"
ALGORITHM = "HS256"

class OfficerPrincipal(BaseModel):
    officer_id: str
    role: str
    sub: Optional[str] = None

class LoginRequest(BaseModel):
    officer_id: str
    password: str

@router.post("/login")
def officer_login(req: LoginRequest):
    if req.officer_id.startswith("NDRF") or req.officer_id in ["admin", "officer"]:
        role = "COMMANDER" if "COMMAND" in req.officer_id.upper() or req.officer_id == "admin" else "DISPATCHER"
        payload = {
            "sub": req.officer_id,
            "officer_id": req.officer_id,
            "role": role,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=12)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return {
            "access_token": token,
            "token_type": "bearer",
            "officer_id": req.officer_id,
            "role": role
        }
    raise HTTPException(status_code=401, detail="Invalid Officer Credentials")

def get_current_officer(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> OfficerPrincipal:
    if not credentials:
        return OfficerPrincipal(officer_id="NDRF_DEMO_OFFICER", role="COMMANDER", sub="NDRF_DEMO_OFFICER")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return OfficerPrincipal(
            officer_id=payload.get("officer_id", payload.get("sub", "NDRF_OFFICER")),
            role=payload.get("role", "COMMANDER"),
            sub=payload.get("sub")
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Command Officer JWT"
        )

def require_role(*allowed_roles):
    # Handles both require_role("A", "B") and require_role(["A", "B"])
    if len(allowed_roles) == 1 and isinstance(allowed_roles[0], (list, tuple)):
        roles_set = set(allowed_roles[0])
    else:
        roles_set = set(allowed_roles)

    def role_checker(officer: OfficerPrincipal = Depends(get_current_officer)):
        if officer.role not in roles_set and "COMMANDER" not in roles_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions for this operation"
            )
        return officer
    return role_checker

verify_officer_token = get_current_officer