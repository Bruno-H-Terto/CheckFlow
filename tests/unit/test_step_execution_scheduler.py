from domain.entities.step import JsonValue
from app.services import StepExecutionScheduler


class SpyEventPublisher:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, dict[str, JsonValue]]] = []

    def publish(
        self,
        topic: str,
        key: str,
        payload: dict[str, JsonValue],
    ) -> None:
        self.messages.append((topic, key, payload))


def test_schedules_step_execution_as_versioned_event() -> None:
    publisher = SpyEventPublisher()
    scheduler = StepExecutionScheduler(publisher)

    event = scheduler.schedule(step_id=42)

    assert event.event_type == "step.execution.requested.v1"
    assert publisher.messages == [
        (
            "checkflow.step-executions",
            "42",
            event.to_payload(),
        )
    ]
