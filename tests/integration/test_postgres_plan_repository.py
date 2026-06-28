# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from testcontainers.postgres import PostgresContainer

from adapters.postgres import PostgresPlanRepository, PostgresStepRepository
from domain.entities.flow_validator import Plan
from domain.entities.step import (
    AssertionTarget,
    HttpAction,
    HttpMethod,
    Step,
    StepAssertion,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="set RUN_INTEGRATION_TESTS=1 to run PostgreSQL tests",
    ),
]


@pytest.fixture(scope="module")
def repositories() -> Iterator[tuple[PostgresPlanRepository, PostgresStepRepository]]:
    with PostgresContainer("postgres:17-alpine", driver="psycopg") as postgres:
        database_url = postgres.get_connection_url()
        alembic_config = Config("alembic.ini")
        alembic_config.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(alembic_config, "head")

        engine = create_engine(database_url)
        yield PostgresPlanRepository(engine), PostgresStepRepository(engine)
        engine.dispose()
        command.downgrade(alembic_config, "base")


def test_postgres_plan_crud(
    repositories: tuple[PostgresPlanRepository, PostgresStepRepository],
) -> None:
    repository, _ = repositories
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


def test_postgres_step_crud_with_jsonb(
    repositories: tuple[PostgresPlanRepository, PostgresStepRepository],
) -> None:
    plan_repository, step_repository = repositories
    plan = plan_repository.add(Plan(name="Order consistency"))
    assert plan.id is not None
    action = HttpAction(
        HttpMethod.POST,
        "https://orders.local/orders",
        body={"product_id": 42},
    )
    assertions = (
        StepAssertion(AssertionTarget.STATUS_CODE, 201),
        StepAssertion(AssertionTarget.BODY, "created", path="status"),
    )

    second = step_repository.add(Step(plan.id, 2, "Read order", action, assertions))
    first = step_repository.add(Step(plan.id, 1, "Create order", action, assertions))

    assert step_repository.list_by_plan(plan.id) == [first, second]
    assert step_repository.get(plan.id, first.id or 0) == first

    updated = step_repository.update(
        Step(
            plan_id=plan.id,
            id=first.id,
            sequence=1,
            name="Submit order",
            action=action,
            assertions=assertions,
            created_at=first.created_at,
            updated_at=first.updated_at,
        )
    )
    assert updated.name == "Submit order"

    assert step_repository.delete(plan.id, first.id or 0) is True
    assert step_repository.get(plan.id, first.id or 0) is None
    assert step_repository.delete(plan.id, first.id or 0) is False
