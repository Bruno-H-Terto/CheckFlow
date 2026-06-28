from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String, Text, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from domain.entities.flow_validator import Plan


class Base(DeclarativeBase):
    pass


class PlanModel(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PostgresPlanRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @classmethod
    def from_url(cls, database_url: str) -> "PostgresPlanRepository":
        return cls(create_engine(database_url, pool_pre_ping=True))

    def close(self) -> None:
        self._engine.dispose()

    def add(self, plan: Plan) -> Plan:
        model = PlanModel(
            name=plan.name,
            description=plan.description,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            deleted_at=plan.deleted_at,
            active=plan.active,
        )
        with Session(self._engine) as session:
            session.add(model)
            session.commit()
            session.refresh(model)
            return self._to_entity(model)

    def get(self, plan_id: int) -> Plan | None:
        statement = select(PlanModel).where(
            PlanModel.id == plan_id,
            PlanModel.deleted_at.is_(None),
        )
        with Session(self._engine) as session:
            model = session.scalar(statement)
            return None if model is None else self._to_entity(model)

    def list(self) -> list[Plan]:
        statement = (
            select(PlanModel)
            .where(PlanModel.deleted_at.is_(None))
            .order_by(PlanModel.id)
        )
        with Session(self._engine) as session:
            return [self._to_entity(model) for model in session.scalars(statement)]

    def update(self, plan: Plan) -> Plan:
        if plan.id is None:
            raise ValueError("Cannot update a plan without an id")

        with Session(self._engine) as session:
            model = session.get(PlanModel, plan.id)
            if model is None or model.deleted_at is not None:
                raise ValueError(f"Plan {plan.id} does not exist")
            model.name = plan.name
            model.description = plan.description
            model.updated_at = plan.updated_at
            model.active = plan.active
            session.commit()
            session.refresh(model)
            return self._to_entity(model)

    def delete(self, plan_id: int) -> bool:
        with Session(self._engine) as session:
            model = session.get(PlanModel, plan_id)
            if model is None or model.deleted_at is not None:
                return False
            model.deleted_at = datetime.now(UTC)
            model.active = False
            session.commit()
            return True

    @staticmethod
    def _to_entity(model: PlanModel) -> Plan:
        return Plan(
            id=model.id,
            name=model.name,
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            active=model.active,
        )
