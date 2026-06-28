import json
import sqlite3
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import cast

from domain.entities.internal_log import InternalLog, LogLevel


class SqliteInternalLogRepository:
    def __init__(self, database_path: str | Path) -> None:
        self._connection = sqlite3.connect(database_path)
        self._create_schema()

    def _create_schema(self) -> None:
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS internal_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                context TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """)
        self._connection.commit()

    def save(self, log: InternalLog) -> InternalLog:
        cursor = self._connection.execute(
            """
            INSERT INTO internal_logs (level, message, context, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                log.level.value,
                log.message,
                json.dumps(log.context),
                log.created_at.isoformat(),
            ),
        )
        self._connection.commit()
        log_id = cursor.lastrowid
        if log_id is None:
            raise RuntimeError("SQLite did not return an id for the internal log")
        return log.with_id(log_id)

    def list_recent(self, limit: int = 100) -> list[InternalLog]:
        if limit < 1:
            raise ValueError("limit must be greater than zero")

        rows = self._connection.execute(
            """
            SELECT id, level, message, context, created_at
            FROM internal_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [self._to_log(row) for row in rows]

    @staticmethod
    def _to_log(row: tuple[object, ...]) -> InternalLog:
        log_id, level, message, raw_context, created_at = row
        context = cast(Mapping[str, str], json.loads(cast(str, raw_context)))
        return InternalLog(
            id=cast(int, log_id),
            level=LogLevel(cast(str, level)),
            message=cast(str, message),
            context=dict(context),
            created_at=datetime.fromisoformat(cast(str, created_at)),
        )

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SqliteInternalLogRepository":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
