from dataclasses import replace
from datetime import UTC, datetime

from app.ports.plan_repository import PlanRepository
from domain.entities.flow_validator import Plan


class PlanNotFoundError(Exception):
    def __init__(self, plan_id: int) -> None:
        super().__init__(f"Plan {plan_id} was not found")
        self.plan_id = plan_id


class PlanService:
    def __init__(self, repository: PlanRepository) -> None:
        self._repository = repository

    def create(self, name: str, description: str | None = "") -> Plan:
        return self._repository.add(Plan(name=name, description=description))

    def get(self, plan_id: int) -> Plan:
        plan = self._repository.get(plan_id)
        if plan is None:
            raise PlanNotFoundError(plan_id)
        return plan

    def list(self) -> list[Plan]:
        return self._repository.list()

    def update(
        self,
        plan_id: int,
        name: str,
        description: str | None,
        active: bool,
    ) -> Plan:
        plan = self.get(plan_id)
        updated_plan = replace(
            plan,
            name=name,
            description=description,
            active=active,
            updated_at=datetime.now(UTC),
        )
        return self._repository.update(updated_plan)

    def delete(self, plan_id: int) -> None:
        if not self._repository.delete(plan_id):
            raise PlanNotFoundError(plan_id)
