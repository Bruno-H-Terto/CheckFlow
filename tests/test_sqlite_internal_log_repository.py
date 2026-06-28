from collections.abc import Iterator
from pathlib import Path

import pytest

from adapters.sqlite import SqliteInternalLogRepository
from app.ports.internal_log_repository import InternalLogRepository
from domain.entities.internal_log import InternalLog, LogLevel


@pytest.fixture
def repository(tmp_path: Path) -> Iterator[SqliteInternalLogRepository]:
    repository = SqliteInternalLogRepository(tmp_path / "internal-logs.sqlite3")
    yield repository
    repository.close()


def test_saves_and_lists_internal_logs(
    repository: SqliteInternalLogRepository,
) -> None:
    log = InternalLog(
        level=LogLevel.ERROR,
        message="Flow execution failed",
        context={"plan_id": "42"},
    )

    saved_log = repository.save(log)

    assert saved_log.id == 1
    assert repository.list_recent() == [saved_log]


def test_implements_internal_log_repository_port(
    repository: SqliteInternalLogRepository,
) -> None:
    port: InternalLogRepository = repository

    assert port.list_recent() == []


def test_rejects_invalid_list_limit(
    repository: SqliteInternalLogRepository,
) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        repository.list_recent(limit=0)
