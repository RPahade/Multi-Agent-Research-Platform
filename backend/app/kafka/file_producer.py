"""File-replay producer: read events from a JSONL file and publish them.

Each non-empty, non-comment line is a JSON object validated against ``JobEvent``
(missing event_id/timestamp are filled with defaults), then published to the topic.

Usage:
    python -m app.kafka.file_producer [path/to/events.jsonl]
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from app.core.config import settings
from app.core.logging import configure_logging
from app.schemas.events import JobEvent

logger = logging.getLogger("kafka.file_producer")

_DEFAULT_FILE = "samples/job_events.jsonl"


def publish_file(path: str) -> int:
    from confluent_kafka import Producer

    producer = Producer({"bootstrap.servers": settings.kafka_bootstrap_servers, "client.id": "mari-file-producer"})

    def _cb(err, msg):
        if err is not None:
            logger.warning("delivery failed: %s", err)

    count = 0
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        event = JobEvent(**json.loads(line))  # validate + fill defaults
        producer.produce(
            settings.kafka_topic,
            key=event.job_id,
            value=event.model_dump_json().encode("utf-8"),
            callback=_cb,
        )
        producer.poll(0)
        count += 1

    producer.flush(10)
    logger.info("Published %d events from %s to topic '%s'", count, path, settings.kafka_topic)
    return count


def main() -> None:
    configure_logging()
    path = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_FILE
    publish_file(path)


if __name__ == "__main__":
    main()
