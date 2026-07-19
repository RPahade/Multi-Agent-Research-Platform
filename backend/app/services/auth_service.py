"""Authentication business logic: login, refresh-token rotation, and logout."""

from __future__ import annotations

from datetime import datetime, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.security import REFRESH_TOKEN_TYPE
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import TokenPair
from app.services import user_service


class AuthError(Exception):
    """Raised on any authentication failure (mapped to HTTP 401 by the route)."""


def authenticate(db: Session, email: str, password: str) -> User:
    """Return the user for valid credentials, else raise ``AuthError``."""
    user = user_service.get_by_email(db, email)
    if user is None or not user.hashed_password:
        raise AuthError("Invalid email or password")
    if not security.verify_password(password, user.hashed_password):
        raise AuthError("Invalid email or password")
    if not user.is_active:
        raise AuthError("User account is inactive")
    return user


def _persist_refresh(db: Session, user: User, issued: security.IssuedToken, user_agent: str | None) -> None:
    db.add(
        RefreshToken(
            user_id=user.id,
            jti=issued.jti,
            expires_at=issued.expires_at,
            user_agent=user_agent,
        )
    )


def issue_token_pair(db: Session, user: User, *, user_agent: str | None = None) -> TokenPair:
    """Mint an access+refresh pair and record the refresh token's jti."""
    access = security.create_access_token(str(user.id), user.role.value)
    refresh = security.create_refresh_token(str(user.id))
    _persist_refresh(db, user, refresh, user_agent)
    db.commit()
    return TokenPair(access_token=access.token, refresh_token=refresh.token)


def _decode_refresh(token: str) -> dict:
    try:
        payload = security.decode_token(token)
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid or expired refresh token") from exc
    if payload.get("type") != REFRESH_TOKEN_TYPE:
        raise AuthError("Not a refresh token")
    return payload


def _get_active_refresh_row(db: Session, jti: str) -> RefreshToken | None:
    row = db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if row is None or row.revoked_at is not None:
        return None
    if row.expires_at <= datetime.now(timezone.utc):
        return None
    return row


def rotate_refresh_token(db: Session, token: str, *, user_agent: str | None = None) -> TokenPair:
    """Validate a refresh token, revoke it, and issue a fresh pair (rotation)."""
    payload = _decode_refresh(token)
    row = _get_active_refresh_row(db, payload.get("jti", ""))
    if row is None:
        raise AuthError("Refresh token is revoked or expired")

    user = user_service.get_by_id(db, payload["sub"])
    if user is None or not user.is_active:
        raise AuthError("User not found or inactive")

    # Rotate: revoke the presented token, then issue a new pair.
    row.revoked_at = datetime.now(timezone.utc)
    access = security.create_access_token(str(user.id), user.role.value)
    refresh = security.create_refresh_token(str(user.id))
    _persist_refresh(db, user, refresh, user_agent)
    db.commit()
    return TokenPair(access_token=access.token, refresh_token=refresh.token)


def logout(db: Session, token: str) -> None:
    """Revoke the given refresh token so it can no longer be used."""
    try:
        payload = _decode_refresh(token)
    except AuthError:
        # Treat an unparasable/expired token as already logged out (idempotent).
        return
    row = _get_active_refresh_row(db, payload.get("jti", ""))
    if row is not None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()
