"""Logging configuration.

Provides a single ``configure_logging`` entrypoint called on app startup so the
whole process shares one consistent, level-configurable log format.
"""

from __future__ import annotations

import logging
from logging.config import dictConfig

from app.core.config import settings


def configure_logging() -> None:
    """Configure root logging using the level from settings."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {
                "level": settings.log_level.upper(),
                "handlers": ["console"],
            },
            "loggers": {
                # Keep uvicorn access/error logs consistent with our format.
                "uvicorn": {"level": settings.log_level.upper(), "propagate": True},
                "uvicorn.error": {"level": settings.log_level.upper(), "propagate": True},
                "uvicorn.access": {"level": settings.log_level.upper(), "propagate": True},
            },
        }
    )
    logging.getLogger(__name__).debug("Logging configured (level=%s)", settings.log_level)
