"""Security primitives: password hashing (bcrypt) and JWT create/decode.

Kept free of any DB or FastAPI imports so it is trivially unit-testable.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

# bcrypt has a hard 72-byte limit on the input; enforce it at the schema layer.
_BCRYPT_MAX_BYTES = 72

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


# --- Passwords ---------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt; returns the encoded hash string."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- JWT ---------------------------------------------------------------------

@dataclass(frozen=True)
class IssuedToken:
    """A freshly-minted token plus the fields callers need to persist/return."""

    token: str
    jti: str
    expires_at: datetime


def _create_token(
    *,
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    role: str | None = None,
) -> IssuedToken:
    now = datetime.now(timezone.utc)
    expires_at = now + expires_delta
    jti = str(uuid.uuid4())
    payload: dict = {
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }
    if role is not None:
        payload["role"] = role
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return IssuedToken(token=token, jti=jti, expires_at=expires_at)


def create_access_token(user_id: str, role: str) -> IssuedToken:
    """Short-lived access token carrying the user's id and role."""
    return _create_token(
        subject=str(user_id),
        token_type=ACCESS_TOKEN_TYPE,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        role=role,
    )


def create_refresh_token(user_id: str) -> IssuedToken:
    """Longer-lived refresh token; its jti is tracked in the DB for revocation."""
    return _create_token(
        subject=str(user_id),
        token_type=REFRESH_TOKEN_TYPE,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict:
    """Decode & verify a JWT. Raises ``jwt.PyJWTError`` on any failure."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
