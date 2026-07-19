"""User-related business logic: lookup, creation, and first-admin seeding."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User

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
