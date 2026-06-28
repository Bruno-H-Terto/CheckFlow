from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from domain.entities.step import JsonValue


@dataclass(frozen=True, slots=True)
class StepExecutionRequested:
    step_id: int
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def event_type(self) -> str:
        return "step.execution.requested.v1"

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "step_id": self.step_id,
        }
