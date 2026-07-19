"""User-related business logic: lookup, creation, and first-admin seeding."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User
from app.services import crud

logger = logging.getLogger(__name__)


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))


def get_by_id(db: Session, user_id: uuid.UUID | str) -> User | None:
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        return None
    return user


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.deleted_at.is_(None)).order_by(User.created_at)))


def list_users_page(
    db: Session,
    *,
    page: int,
    size: int,
    role: UserRole | None = None,
    is_active: bool | None = None,
    q: str | None = None,
) -> tuple[list[User], int]:
    stmt = select(User).where(User.deleted_at.is_(None))
    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(User.email.ilike(like), User.full_name.ilike(like)))
    stmt = stmt.order_by(User.created_at.desc())
    return crud.paginate(db, stmt, page, size)


def update_user(db: Session, user: User, data: dict) -> User:
    """Apply a partial update; ``password`` (if present) is re-hashed."""
    if "password" in data:
        password = data.pop("password")
        if password:
            user.hashed_password = hash_password(password)
    for field, value in data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def soft_delete_user(db: Session, user: User) -> None:
    user.deleted_at = datetime.now(timezone.utc)
    db.commit()


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str | None = None,
    role: UserRole = UserRole.ANALYST,
) -> User:
    """Create and persist a new user. Caller must ensure the email is unique."""
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed_first_admin(db: Session) -> None:
    """Create the bootstrap admin from settings if configured and not present."""
    email = settings.first_admin_email
    password = settings.first_admin_password
    if not email or not password:
        logger.info("First-admin seeding skipped (FIRST_ADMIN_EMAIL/PASSWORD not set).")
        return
    if get_by_email(db, email) is not None:
        logger.info("First-admin already exists (%s); nothing to seed.", email)
        return
    create_user(
        db,
        email=email,
        password=password,
        full_name=settings.first_admin_name,
        role=UserRole.ADMIN,
    )
    logger.info("Seeded first admin user: %s", email)
