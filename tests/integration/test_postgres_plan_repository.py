# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from testcontainers.postgres import PostgresContainer

from adapters.postgres import PostgresPlanRepository
from domain.entities.flow_validator import Plan


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="set RUN_INTEGRATION_TESTS=1 to run PostgreSQL tests",
    ),
]


@pytest.fixture(scope="module")
def repository() -> Iterator[PostgresPlanRepository]:
    with PostgresContainer("postgres:17-alpine", driver="psycopg") as postgres:
        database_url = postgres.get_connection_url()
        alembic_config = Config("alembic.ini")
        alembic_config.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(alembic_config, "head")

        engine = create_engine(database_url)
        repository = PostgresPlanRepository(engine)
        yield repository
        engine.dispose()
        command.downgrade(alembic_config, "base")


def test_postgres_plan_crud(repository: PostgresPlanRepository) -> None:
    created = repository.add(Plan(name="Distributed checkout"))

    assert created.id is not None
    assert repository.get(created.id) == created

    updated = repository.update(
        Plan(
            id=created.id,
            name="Reliable checkout",
            description="Updated in PostgreSQL",
            created_at=created.created_at,
            updated_at=created.updated_at,
        )
    )
    assert updated.name == "Reliable checkout"
    assert repository.list() == [updated]

    assert repository.delete(created.id) is True
    assert repository.get(created.id) is None
    assert repository.delete(created.id) is False
