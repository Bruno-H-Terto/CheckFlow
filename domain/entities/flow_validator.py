from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import IntEnum


class StatusCode(IntEnum):
    QUEUED = 0
    STARTED = 5
    PROGRESS = 10
    COMPLETED = 15
    FAILED = 20


@dataclass(frozen=True, slots=True)
class Plan:
    name: str
    id: int | None = None
    description: str | None = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None
    active: bool = True


@dataclass(frozen=True, slots=True)
class CheckPoint:
    id: int
    sequence: int
    plan: Plan
    status: StatusCode
