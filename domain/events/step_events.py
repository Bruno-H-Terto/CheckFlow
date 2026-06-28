from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from domain.entities.step import JsonValue


class ExecutionControl(StrEnum):
    STOP = "stop"
    RESTART = "restart"


def _identifier() -> str:
    return str(uuid4())


@dataclass(frozen=True, slots=True)
class StepExecutionRequested:
    step_id: int
    execution_id: str = field(default_factory=_identifier)
    event_id: str = field(default_factory=_identifier)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def event_type(self) -> str:
        return "step.execution.requested.v1"

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "execution_id": self.execution_id,
            "step_id": self.step_id,
        }


@dataclass(frozen=True, slots=True)
class StepExecutionScheduled:
    step_id: int
    scheduled_for: datetime
    execution_id: str = field(default_factory=_identifier)
    event_id: str = field(default_factory=_identifier)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def event_type(self) -> str:
        return "step.execution.scheduled.v1"

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "execution_id": self.execution_id,
            "step_id": self.step_id,
            "scheduled_for": self.scheduled_for.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class StepExecutionControlRequested:
    execution_id: str
    step_id: int
    command: ExecutionControl
    event_id: str = field(default_factory=_identifier)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def event_type(self) -> str:
        return f"step.execution.{self.command.value}-requested.v1"

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "execution_id": self.execution_id,
            "step_id": self.step_id,
            "command": self.command.value,
        }
