# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from typing import cast

import httpx
import pytest
from confluent_kafka import Consumer, Producer
from redis import Redis

from adapters.http import HttpxActionRunner
from adapters.kafka import KafkaEventConsumer, KafkaEventPublisher
from adapters.redis import RedisJsonCache
from domain.entities.step import HttpAction, HttpMethod


class FakeProducer:
    def __init__(self) -> None:
        self.messages: list[tuple[str, bytes, bytes]] = []
        self.flushes = 0

    def produce(self, topic: str, key: bytes, value: bytes) -> None:
        self.messages.append((topic, key, value))

    def flush(self, _timeout: float) -> None:
        self.flushes += 1


class FakeMessage:
    def error(self) -> None:
        return None

    def value(self) -> bytes:
        return b'{"step_id": 42}'


class FakeConsumer:
    def __init__(self) -> None:
        self.polls = 0
        self.committed = False
        self.closed = False

    def subscribe(self, _topics: list[str]) -> None:
        pass

    def poll(self, _timeout: float) -> FakeMessage:
        self.polls += 1
        if self.polls > 1:
            raise KeyboardInterrupt
        return FakeMessage()

    def commit(self, **_kwargs: object) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self.values[key] = value

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def delete(self, key: str) -> None:
        self.values.pop(key, None)

    def close(self) -> None:
        pass


def test_kafka_publisher_serializes_json() -> None:
    producer = FakeProducer()
    publisher = KafkaEventPublisher("unused", cast(Producer, producer))

    publisher.publish("events", "42", {"step_id": 42})
    publisher.close()

    assert producer.messages == [("events", b"42", b'{"step_id": 42}')]
    assert producer.flushes == 2


def test_kafka_consumer_commits_after_handler() -> None:
    raw_consumer = FakeConsumer()
    consumer = KafkaEventConsumer(
        "unused",
        "group",
        ["events"],
        cast(Consumer, raw_consumer),
    )
    received: list[object] = []

    with pytest.raises(KeyboardInterrupt):
        consumer.run(received.append)

    assert received == [{"step_id": 42}]
    assert raw_consumer.committed is True
    assert raw_consumer.closed is True


def test_redis_json_cache_round_trip() -> None:
    cache = RedisJsonCache("redis://unused", client=cast(Redis, FakeRedis()))

    cache.set("execution:1", {"state": "started"})
    assert cache.get("execution:1") == {"state": "started"}
    cache.delete("execution:1")
    assert cache.get("execution:1") is None
    cache.close()


def test_http_action_runner_captures_response(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(201, json={"status": "created"})

    def fake_request(**_kwargs: object) -> httpx.Response:
        return response

    monkeypatch.setattr(httpx, "request", fake_request)

    result = HttpxActionRunner().run(
        HttpAction(HttpMethod.POST, "https://orders.local/orders")
    )

    assert result.status_code == 201
    assert result.body == {"status": "created"}
