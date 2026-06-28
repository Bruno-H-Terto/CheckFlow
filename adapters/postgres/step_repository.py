from datetime import UTC, datetime
from typing import cast

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, Session, mapped_column

from adapters.postgres.plan_repository import Base
from adapters.postgres.plan_repository import PlanModel
from domain.entities.step import (
    AssertionOperator,
    AssertionTarget,
    HttpAction,
    HttpMethod,
    JsonValue,
    Step,
    StepAssertion,
)


class StepModel(Base):
    __tablename__ = "steps"
    __table_args__ = (UniqueConstraint("plan_id", "sequence"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[dict[str, JsonValue]] = mapped_column(JSONB, nullable=False)
    assertions: Mapped[list[dict[str, JsonValue]]] = mapped_column(
        JSONB, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PostgresStepRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @classmethod
    def from_url(cls, database_url: str) -> "PostgresStepRepository":
        return cls(create_engine(database_url, pool_pre_ping=True))

    def close(self) -> None:
        self._engine.dispose()

    def add(self, plan_id: int, step: Step) -> Step:
        statement = select(PlanModel).where(
            PlanModel.id == plan_id,
            PlanModel.deleted_at.is_(None)
        )
        
        model = self._to_model(step)
        with Session(self._engine) as session:
            plan = session.scalar(statement)
            if plan is None:
                raise ValueError(f"Not found plan with id {plan_id}")
        
            session.add(model)
            session.commit()
            session.refresh(model)

            return self._to_entity(model)

    def get(self, plan_id: int, step_id: int) -> Step | None:
        statement = select(StepModel).where(
            StepModel.plan_id == plan_id,
            StepModel.id == step_id,
            StepModel.deleted_at.is_(None),
        )

        with Session(self._engine) as session:
            model = session.scalar(statement)
            return None if model is None else self._to_entity(model)

    def list_by_plan(self, plan_id: int) -> list[Step]:
        statement = (
            select(StepModel)
            .where(StepModel.plan_id == plan_id, StepModel.deleted_at.is_(None))
            .order_by(StepModel.sequence)
        )
        with Session(self._engine) as session:
            return [self._to_entity(model) for model in session.scalars(statement)]

    def update(self, plan_id: int, step: Step) -> Step:
        if step.id is None:
            raise ValueError("Cannot update a step without an id")

        statement = select(StepModel).where(
            StepModel.plan_id == plan_id,
            StepModel.id == step.id,
            StepModel.deleted_at.is_(None),
        )

        with Session(self._engine) as session:
            model = session.scalar(statement)

            if model is None:
                raise ValueError(f"Step {step.id} does not exist in plan {plan_id}")

            model.sequence = step.sequence
            model.name = step.name
            model.description = step.description
            model.action = self._action_payload(step.action)
            model.assertions = self._assertion_payloads(step.assertions)
            model.updated_at = step.updated_at
            model.active = step.active

            session.commit()
            session.refresh(model)

            return self._to_entity(model)

    def delete(self, plan_id: int, step_id: int) -> bool:
        statement = select(StepModel).where(
            StepModel.plan_id == plan_id,
            StepModel.id == step_id,
            StepModel.deleted_at.is_(None),
        )

        with Session(self._engine) as session:
            step = session.scalar(statement)

            if step is None:
                return False

            step.deleted_at = datetime.now(UTC)
            step.active = False
            session.commit()

            return True

    @classmethod
    def _to_model(cls, step: Step) -> StepModel:
        return StepModel(
            plan_id=step.plan_id,
            sequence=step.sequence,
            name=step.name,
            description=step.description,
            action=cls._action_payload(step.action),
            assertions=cls._assertion_payloads(step.assertions),
            created_at=step.created_at,
            updated_at=step.updated_at,
            deleted_at=step.deleted_at,
            active=step.active,
        )

    @staticmethod
    def _action_payload(action: HttpAction) -> dict[str, JsonValue]:
        headers: dict[str, JsonValue] = dict(action.headers)

        return {
            "type": "http",
            "method": action.method.value,
            "url": action.url,
            "headers": headers,
            "body": action.body,
            "timeout_seconds": action.timeout_seconds,
        }

    @staticmethod
    def _assertion_payloads(
        assertions: tuple[StepAssertion, ...],
    ) -> list[dict[str, JsonValue]]:
        return [
            {
                "target": assertion.target.value,
                "operator": assertion.operator.value,
                "expected": assertion.expected,
                "path": assertion.path,
            }
            for assertion in assertions
        ]

    @staticmethod
    def _to_entity(model: StepModel) -> Step:
        action = model.action
        assertions = model.assertions

        return Step(
            id=model.id,
            plan_id=model.plan_id,
            sequence=model.sequence,
            name=model.name,
            description=model.description,
            action=HttpAction(
                method=HttpMethod(cast(str, action["method"])),
                url=cast(str, action["url"]),
                headers=cast(dict[str, str], action.get("headers", {})),
                body=action.get("body"),
                timeout_seconds=cast(float, action.get("timeout_seconds", 30.0)),
            ),
            assertions=tuple(
                StepAssertion(
                    target=AssertionTarget(cast(str, item["target"])),
                    operator=AssertionOperator(cast(str, item["operator"])),
                    expected=item.get("expected"),
                    path=cast(str | None, item.get("path")),
                )
                for item in assertions
            ),
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            active=model.active,
        )
