"""Kafka/events status endpoint (Milestone 7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/status", summary="Kafka event pipeline configuration")
def events_status(_user: User = Depends(get_current_user)) -> dict:
    return {
        "kafka_enabled": settings.kafka_enabled,
        "bootstrap_servers": settings.kafka_bootstrap_servers,
        "topic": settings.kafka_topic,
        "consumer_group": settings.kafka_consumer_group,
    }
