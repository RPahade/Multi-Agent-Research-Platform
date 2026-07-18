"""Database engine and session management.

Sets up the SQLAlchemy engine/session from ``settings.database_url`` and exposes a
``get_db`` FastAPI dependency. No tables are defined yet — ORM models and Alembic
migrations arrive in a later milestone. This module only establishes connectivity.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# ``pool_pre_ping`` transparently recycles stale connections (e.g. after the DB
# container restarts), which keeps long-running background tasks resilient.
engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session, ensuring it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
