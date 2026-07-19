"""Authentication endpoints: login, refresh, logout, and current-user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import MessageResponse, RefreshRequest, TokenPair
from app.schemas.user import UserRead
from app.services import auth_service
from app.services.auth_service import AuthError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair, summary="Log in (email + password)")
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenPair:
    """Authenticate with email (as ``username``) and password; returns a token pair."""
    try:
        user = auth_service.authenticate(db, form.username, form.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return auth_service.issue_token_pair(db, user, user_agent=request.headers.get("user-agent"))


@router.post("/refresh", response_model=TokenPair, summary="Rotate refresh token")
def refresh(
    request: Request,
    body: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenPair:
    """Exchange a valid refresh token for a new pair (old refresh token is revoked)."""
    try:
        return auth_service.rotate_refresh_token(
            db, body.refresh_token, user_agent=request.headers.get("user-agent")
        )
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/logout", response_model=MessageResponse, summary="Revoke a refresh token")
def logout(
    body: RefreshRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> MessageResponse:
    """Revoke the supplied refresh token (requires a valid access token)."""
    auth_service.logout(db, body.refresh_token)
    return MessageResponse(detail="Logged out")


@router.get("/me", response_model=UserRead, summary="Current user")
def me(user: User = Depends(get_current_user)) -> User:
    """Return the profile of the currently authenticated user."""
    return user
