from typing import Protocol

from domain.entities.internal_log import InternalLog


class InternalLogRepository(Protocol):
    def save(self, log: InternalLog) -> InternalLog: ...

    def list_recent(self, limit: int = 100) -> list[InternalLog]: ...
