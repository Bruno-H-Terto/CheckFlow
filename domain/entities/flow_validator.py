from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any

from domain.entities.assert_support import CallBase, Http


ASSERT_SUPPORT: dict[str, type[CallBase]] = {
    "http": Http
}

class StatusCode(IntEnum):
    QUEUED = 0
    STARTED = 5
    PROGRESS = 10
    COMPLETED = 15
    FAILED = 20

@dataclass(frozen=True, slots=True)
class Plan:
    id: int
    name: str
    description: str | None = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    deleted_at: datetime | None = None
    active: bool = True

@dataclass(frozen=True, slots=True)
class CheckPoint:
    id: int
    sequence: int
    plan: Plan
    status: StatusCode


@dataclass(frozen=True, slots=True)
class Assert:
    expected: tuple[dict[Any, Any], ...] | None = ()

@dataclass(frozen=True, slots=True)
class Action:
    id: int
    sequence: int
    _type: str

    def calls(self) -> CallBase:
        return self._run()

    def _run(self) -> CallBase:
        return ASSERT_SUPPORT[self._type]()
    

@dataclass(frozen=True, slots=True)
class Step:
    id: int
    sequence: int
    checkpoint: CheckPoint
    name: str
    status: StatusCode
    description: str | None = ""
    asserts: list[Assert] = field(default_factory=list[Assert])
    action: list[Action] = field(default_factory=list[Action])
    started_in: datetime = field(default_factory=datetime.now)
    finished_in: datetime | None = None
