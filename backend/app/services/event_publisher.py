"""Best-effort Kafka producer for job lifecycle events.

Publishing is fire-and-forget and never breaks job execution: if Kafka is disabled
or unreachable, we log a warning and move on. The confluent-kafka SDK is imported
lazily so the app runs fine without it installed / with Kafka off.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.schemas.events import JobEvent

logger = logging.getLogger(__name__)

_producer = None


def _get_producer():
    global _producer
    if _producer is None:
        from confluent_kafka import Producer

        _producer = Producer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "client.id": "mari-backend",
                "socket.timeout.ms": 3000,
                "message.timeout.ms": 5000,
            }
        )
    return _producer


def _on_delivery(err, msg) -> None:
    if err is not None:
        logger.warning("Kafka delivery failed: %s", err)


def publish_status(
    job_id,
    status,
    *,
    event_type: str | None = None,
    progress: int | None = None,
    current_step: str | None = None,
) -> None:
    """Publish a job event to ``agent.job.events`` (keyed by job_id for ordering)."""
    if not settings.kafka_enabled:
        return
    status_str = status.value if hasattr(status, "value") else str(status)
    try:
        event = JobEvent(
            event_type=event_type or f"job.{status_str}",
            job_id=str(job_id),
            status=status_str,
            progress=progress,
            current_step=current_step,
        )
        producer = _get_producer()
        producer.produce(
            settings.kafka_topic,
            key=str(job_id),
            value=event.model_dump_json().encode("utf-8"),
            callback=_on_delivery,
        )
        producer.poll(0)  # serve delivery callbacks without blocking
    except Exception as exc:  # noqa: BLE001 - never let telemetry break a job
        logger.warning("Kafka publish skipped (%s)", exc)


def flush(timeout: float = 5.0) -> None:
    """Flush pending messages on shutdown."""
    if _producer is not None:
        try:
            _producer.flush(timeout)
        except Exception:  # noqa: BLE001
            logger.warning("Kafka flush failed", exc_info=True)
