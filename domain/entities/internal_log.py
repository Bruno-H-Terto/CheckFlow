from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum


class LogLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class InternalLog:
    message: str
    level: LogLevel = LogLevel.INFO
    context: dict[str, str] = field(default_factory=dict[str, str])
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: int | None = None

    def with_id(self, log_id: int) -> "InternalLog":
        return replace(self, id=log_id)
