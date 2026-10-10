from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .security import decode_access_token
from .database import get_global_db, get_tenant_db

bearer_scheme = HTTPBearer()


def _get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return payload


def get_current_user(payload: dict = Depends(_get_token_payload)) -> dict:
    return payload


def require_creator_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "creator_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Creator admin access required")
    return user


def require_super_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required")
    return user


def require_hospital_staff(user: dict = Depends(get_current_user)) -> dict:
    """Allows super_admin, doctor, patient — anyone from a hospital tenant."""
    if user.get("role") not in ("super_admin", "doctor", "patient"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hospital staff access required")
    return user


def get_tenant_session(user: dict = Depends(get_current_user)) -> Generator[Session, None, None]:
    """Yield a DB session for the tenant DB encoded in the JWT."""
    db_name = user.get("db_name")
    if not db_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hospital context in token")
    yield from get_tenant_db(db_name)
