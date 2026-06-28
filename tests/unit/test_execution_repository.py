from typing import cast

from sqlalchemy import Table, create_engine

from adapters.postgres.execution_repository import (
    PlanExecutionModel,
    PostgresExecutionRepository,
    StepExecutionModel,
)
from adapters.postgres.plan_repository import Base
from domain.entities.execution import ExecutionStatus, PlanExecution


def test_persists_execution_history_results_and_variables() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    tables = [
        cast(Table, PlanExecutionModel.__table__),
        cast(Table, StepExecutionModel.__table__),
    ]
    Base.metadata.create_all(engine, tables=tables)
    repository = PostgresExecutionRepository(engine)
    execution = PlanExecution(id="execution-1", plan_id=1, variables={"tenant": "acme"})

    assert repository.create(execution) == execution
    assert repository.get("missing") is None
    assert repository.list_by_plan(1)[0].status == ExecutionStatus.PENDING

    repository.set_plan_status(execution.id, ExecutionStatus.RUNNING)
    repository.merge_variables(execution.id, {"token": "jwt"})
    repository.start_step(execution.id, 10)
    repository.finish_step(
        execution.id,
        10,
        ExecutionStatus.COMPLETED,
        status_code=201,
        latency_ms=3.5,
        assertions=[{"passed": True}],
    )
    repository.set_plan_status(execution.id, ExecutionStatus.COMPLETED)

    saved = repository.get(execution.id)
    assert saved is not None
    assert saved.status == ExecutionStatus.COMPLETED
    assert saved.variables == {"tenant": "acme", "token": "jwt"}
    assert saved.started_at is not None and saved.finished_at is not None
    steps = repository.list_steps(execution.id)
    assert steps[0].status_code == 201
    assert steps[0].assertions == [{"passed": True}]
    repository.close()
