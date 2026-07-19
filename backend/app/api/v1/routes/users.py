"""User CRUD endpoints (admin-only) — also demonstrates RBAC enforcement."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.utils import get_active_or_404
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=Page[UserRead], summary="List users (paginated, filtered)")
def list_users(
    pg: PageParams = Depends(),
    role: UserRole | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    q: str | None = Query(default=None, description="search email/name"),
    db: Session = Depends(get_db),
) -> Page[UserRead]:
    items, total = user_service.list_users_page(
        db, page=pg.page, size=pg.size, role=role, is_active=is_active, q=q
    )
    return Page[UserRead].create([UserRead.model_validate(u) for u in items], total, pg)


@router.get("/{user_id}", response_model=UserRead, summary="Get a user")
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> User:
    return get_active_or_404(db, User, user_id, "User")


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED, summary="Create a user")
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    if user_service.get_by_email(db, payload.email) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with this email already exists")
    return user_service.create_user(
        db,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role=payload.role,
    )


@router.patch("/{user_id}", response_model=UserRead, summary="Update a user")
def update_user(user_id: uuid.UUID, payload: UserUpdate, db: Session = Depends(get_db)) -> User:
    user = get_active_or_404(db, User, user_id, "User")
    return user_service.update_user(db, user, payload.model_dump(exclude_unset=True))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a user (soft)")
def delete_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    user = get_active_or_404(db, User, user_id, "User")
    user_service.soft_delete_user(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
