from typing import Protocol

from domain.entities.step import JsonValue


class EventPublisher(Protocol):
    def publish(
        self,
        topic: str,
        key: str,
        payload: dict[str, JsonValue],
    ) -> None: ...
