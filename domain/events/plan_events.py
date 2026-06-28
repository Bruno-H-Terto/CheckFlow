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
class PlanExecutionRequested:
    plan_id: int
    execution_id: str = field(default_factory=_identifier)
    event_id: str = field(default_factory=_identifier)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def event_type(self) -> str:
        return "plan.execution.requested.v1"

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
        }


@dataclass(frozen=True, slots=True)
class PlanExecutionScheduled:
    plan_id: int
    scheduled_for: datetime
    execution_id: str = field(default_factory=_identifier)
    event_id: str = field(default_factory=_identifier)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def event_type(self) -> str:
        return "plan.execution.scheduled.v1"

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "scheduled_for": self.scheduled_for.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class PlanExecutionControlRequested:
    execution_id: str
    plan_id: int
    command: ExecutionControl
    event_id: str = field(default_factory=_identifier)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def event_type(self) -> str:
        return f"plan.execution.{self.command.value}-requested.v1"

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "command": self.command.value,
        }
