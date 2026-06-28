from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from domain.entities.step import JsonValue


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class PlanExecution:
    id: str
    plan_id: int
    status: ExecutionStatus = ExecutionStatus.PENDING
    variables: dict[str, JsonValue] = field(default_factory=dict[str, JsonValue])
    retry_of: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class StepExecution:
    id: int
    execution_id: str
    step_id: int
    status: ExecutionStatus
    status_code: int | None = None
    latency_ms: float | None = None
    assertions: list[dict[str, JsonValue]] = field(default_factory=list[dict[str, JsonValue]])
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
