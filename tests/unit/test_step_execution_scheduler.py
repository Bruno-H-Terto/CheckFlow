from domain.entities.step import JsonValue
from app.services import PlanExecutionScheduler
from datetime import UTC, datetime, timedelta


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


def test_schedules_plan_execution_as_versioned_event() -> None:
    publisher = SpyEventPublisher()
    scheduler = PlanExecutionScheduler(publisher)

    event = scheduler.schedule(plan_id=42)

    assert event.event_type == "plan.execution.requested.v1"
    assert publisher.messages == [
        (
            "checkflow.execution-events",
            event.execution_id,
            event.to_payload(),
        )
    ]


def test_publishes_future_execution_as_scheduled_event() -> None:
    publisher = SpyEventPublisher()
    run_at = datetime.now(UTC) + timedelta(minutes=5)

    event = PlanExecutionScheduler(publisher).schedule(42, run_at)

    assert event.event_type == "plan.execution.scheduled.v1"
    assert publisher.messages[0][0] == "checkflow.execution-events"
