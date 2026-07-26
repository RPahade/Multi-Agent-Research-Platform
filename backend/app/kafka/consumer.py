"""Consumer: subscribe to ``agent.job.events`` and log every message.

Runs as its own container (service ``consumer``). Commits offsets automatically and
shuts down cleanly on SIGINT/SIGTERM.

Usage:
    python -m app.kafka.consumer
"""

from __future__ import annotations

import json
import logging
import signal

from app.core.config import settings
from app.core.logging import configure_logging

logger = logging.getLogger("kafka.consumer")

_running = True


def _stop(*_args) -> None:
    global _running
    _running = False


def main() -> None:
    configure_logging()
    from confluent_kafka import Consumer

    consumer = Consumer(
        {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": settings.kafka_consumer_group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )
    consumer.subscribe([settings.kafka_topic])
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    logger.info(
        "Consumer subscribed to '%s' (group=%s, brokers=%s)",
        settings.kafka_topic,
        settings.kafka_consumer_group,
        settings.kafka_bootstrap_servers,
    )

    try:
        while _running:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                logger.error("Consumer error: %s", msg.error())
                continue
            try:
                event = json.loads(msg.value())
            except (ValueError, TypeError):
                logger.warning("Non-JSON message at offset %s: %r", msg.offset(), msg.value())
                continue
            logger.info(
                "EVENT %-14s | job=%s status=%s progress=%s step=%r ts=%s (p%s@%s)",
                event.get("event_type"),
                event.get("job_id"),
                event.get("status"),
                event.get("progress"),
                event.get("current_step"),
                event.get("timestamp"),
                msg.partition(),
                msg.offset(),
            )
    finally:
        consumer.close()
        logger.info("Consumer stopped")


if __name__ == "__main__":
    main()
