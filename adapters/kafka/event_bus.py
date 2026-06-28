# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false

import json
from collections.abc import Callable
from typing import cast

from confluent_kafka import Consumer, KafkaError, Producer

from domain.entities.step import JsonValue


class KafkaEventPublisher:
    def __init__(
        self,
        bootstrap_servers: str,
        producer: Producer | None = None,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._producer = producer

    def _get_producer(self) -> Producer:
        if self._producer is None:
            self._producer = Producer(
                {
                    "bootstrap.servers": self._bootstrap_servers,
                    "client.id": "checkflow",
                }
            )
        return self._producer

    def publish(
        self,
        topic: str,
        key: str,
        payload: dict[str, JsonValue],
    ) -> None:
        producer = self._get_producer()
        producer.produce(
            topic,
            key=key.encode(),
            value=json.dumps(payload).encode(),
        )
        producer.flush(5)

    def close(self) -> None:
        if self._producer is not None:
            self._producer.flush(5)


class KafkaEventConsumer:
    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        topics: list[str],
        consumer: Consumer | None = None,
    ) -> None:
        self._consumer = consumer or Consumer(
            {
                "bootstrap.servers": bootstrap_servers,
                "group.id": group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        self._consumer.subscribe(topics)

    def run(self, handler: Callable[[dict[str, JsonValue]], None]) -> None:
        try:
            while True:
                message = self._consumer.poll(1.0)
                if message is None:
                    continue
                error = message.error()
                if error is not None:
                    if error.code() != KafkaError._PARTITION_EOF:
                        raise RuntimeError(str(error))
                    continue
                value = message.value()
                if value is None:
                    raise ValueError("Kafka event has no payload")
                payload = json.loads(value.decode())
                if not isinstance(payload, dict):
                    raise ValueError("Kafka event payload must be an object")
                handler(cast(dict[str, JsonValue], payload))
                self._consumer.commit(message=message, asynchronous=False)
        finally:
            self._consumer.close()
