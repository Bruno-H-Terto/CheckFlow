from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, Session, mapped_column

from adapters.postgres.plan_repository import Base
from domain.entities.execution import ExecutionStatus, PlanExecution, StepExecution
from domain.entities.step import JsonValue


class PlanExecutionModel(Base):
    __tablename__ = "plan_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    variables: Mapped[dict[str, JsonValue]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    retry_of: Mapped[str | None] = mapped_column(ForeignKey("plan_executions.id"), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StepExecutionModel(Base):
    __tablename__ = "step_executions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(ForeignKey("plan_executions.id", ondelete="CASCADE"), index=True)
    step_id: Mapped[int] = mapped_column(ForeignKey("steps.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    assertions: Mapped[list[dict[str, JsonValue]]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PostgresExecutionRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @classmethod
    def from_url(cls, database_url: str) -> "PostgresExecutionRepository":
        return cls(create_engine(database_url, pool_pre_ping=True))

    def close(self) -> None:
        self._engine.dispose()

    def create(self, execution: PlanExecution) -> PlanExecution:
        model = PlanExecutionModel(id=execution.id, plan_id=execution.plan_id, status=execution.status.value, variables=execution.variables, retry_of=execution.retry_of, error=execution.error, created_at=execution.created_at, started_at=execution.started_at, finished_at=execution.finished_at)
        with Session(self._engine) as session:
            session.add(model)
            session.commit()
        return execution

    def get(self, execution_id: str) -> PlanExecution | None:
        with Session(self._engine) as session:
            model = session.get(PlanExecutionModel, execution_id)
            return None if model is None else self._plan_entity(model)

    def list_by_plan(self, plan_id: int) -> list[PlanExecution]:
        statement = select(PlanExecutionModel).where(PlanExecutionModel.plan_id == plan_id).order_by(PlanExecutionModel.created_at.desc())
        with Session(self._engine) as session:
            return [self._plan_entity(item) for item in session.scalars(statement)]

    def set_plan_status(self, execution_id: str, status: ExecutionStatus, error: str | None = None) -> None:
        now = datetime.now(UTC)
        with Session(self._engine) as session:
            model = session.get(PlanExecutionModel, execution_id)
            if model is None:
                raise ValueError(f"Execution {execution_id} was not found")
            model.status = status.value
            model.error = error
            if status == ExecutionStatus.RUNNING and model.started_at is None:
                model.started_at = now
            if status in {ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED}:
                model.finished_at = now
            session.commit()

    def merge_variables(self, execution_id: str, variables: dict[str, JsonValue]) -> None:
        with Session(self._engine) as session:
            model = session.get(PlanExecutionModel, execution_id)
            if model is None:
                raise ValueError(f"Execution {execution_id} was not found")
            model.variables = {**model.variables, **variables}
            session.commit()

    def start_step(self, execution_id: str, step_id: int) -> None:
        with Session(self._engine) as session:
            session.add(StepExecutionModel(execution_id=execution_id, step_id=step_id, status=ExecutionStatus.RUNNING.value, assertions=[], started_at=datetime.now(UTC)))
            session.commit()

    def finish_step(self, execution_id: str, step_id: int, status: ExecutionStatus, *, status_code: int | None = None, latency_ms: float | None = None, assertions: list[dict[str, JsonValue]] | None = None, error: str | None = None) -> None:
        statement = select(StepExecutionModel).where(StepExecutionModel.execution_id == execution_id, StepExecutionModel.step_id == step_id).order_by(StepExecutionModel.id.desc())
        with Session(self._engine) as session:
            model = session.scalar(statement)
            if model is None:
                raise ValueError(f"Step execution {execution_id}/{step_id} was not found")
            model.status = status.value
            model.status_code = status_code
            model.latency_ms = latency_ms
            model.assertions = assertions or []
            model.error = error
            model.finished_at = datetime.now(UTC)
            session.commit()

    def list_steps(self, execution_id: str) -> list[StepExecution]:
        statement = select(StepExecutionModel).where(StepExecutionModel.execution_id == execution_id).order_by(StepExecutionModel.id)
        with Session(self._engine) as session:
            return [self._step_entity(item) for item in session.scalars(statement)]

    @staticmethod
    def _plan_entity(model: PlanExecutionModel) -> PlanExecution:
        return PlanExecution(id=model.id, plan_id=model.plan_id, status=ExecutionStatus(model.status), variables=model.variables, retry_of=model.retry_of, error=model.error, created_at=model.created_at, started_at=model.started_at, finished_at=model.finished_at)

    @staticmethod
    def _step_entity(model: StepExecutionModel) -> StepExecution:
        return StepExecution(id=model.id, execution_id=model.execution_id, step_id=model.step_id, status=ExecutionStatus(model.status), status_code=model.status_code, latency_ms=model.latency_ms, assertions=model.assertions, error=model.error, started_at=model.started_at, finished_at=model.finished_at)
