"""Shared FastAPI dependencies: authentication and role-based authorization."""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.services import user_service

# tokenUrl points at the login endpoint so Swagger's "Authorize" button works.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode the access token and return the active user, or raise 401."""
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as exc:
        raise _CREDENTIALS_EXC from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise _CREDENTIALS_EXC
    user_id = payload.get("sub")
    if not user_id:
        raise _CREDENTIALS_EXC

    user = user_service.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXC
    return user


def require_roles(*roles: UserRole):
    """Build a dependency that allows only the given roles."""

    allowed = set(roles)

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return _checker


# Convenience dependencies.
require_admin = require_roles(UserRole.ADMIN)
# Reports may be written by analysts and admins (leadership is read-only).
require_report_writer = require_roles(UserRole.ADMIN, UserRole.ANALYST)
# Jobs may be created/cancelled by analysts and admins (leadership is read-only).
require_job_writer = require_roles(UserRole.ADMIN, UserRole.ANALYST)
