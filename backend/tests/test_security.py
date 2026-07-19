"""Unit tests for password hashing and JWT helpers (no DB required)."""

from __future__ import annotations

import jwt
import pytest

from app.core import security


def test_password_hash_and_verify() -> None:
    hashed = security.hash_password("s3cret-pw")
    assert hashed != "s3cret-pw"
    assert security.verify_password("s3cret-pw", hashed) is True
    assert security.verify_password("wrong", hashed) is False


def test_access_token_roundtrip_carries_role() -> None:
    issued = security.create_access_token("user-123", "admin")
    payload = security.decode_token(issued.token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == security.ACCESS_TOKEN_TYPE
    assert payload["role"] == "admin"
    assert payload["jti"] == issued.jti


def test_refresh_token_has_no_role_and_correct_type() -> None:
    issued = security.create_refresh_token("user-123")
    payload = security.decode_token(issued.token)
    assert payload["type"] == security.REFRESH_TOKEN_TYPE
    assert "role" not in payload


def test_decode_rejects_tampered_token() -> None:
    issued = security.create_access_token("user-123", "analyst")
    with pytest.raises(jwt.PyJWTError):
        security.decode_token(issued.token + "tamper")
