from dataclasses import replace
from datetime import UTC, datetime

from app.ports.step_repository import StepRepository
from domain.entities.step import Step


class StepNotFoundError(Exception):
    def __init__(self, step_id: int) -> None:
        super().__init__(f"Step {step_id} was not found")
        self.step_id = step_id


class StepService:
    def __init__(self, repository: StepRepository) -> None:
        self._repository = repository

    def create(self, step: Step) -> Step:
        return self._repository.add(step)

    def get(self, step_id: int) -> Step:
        step = self._repository.get(step_id)
        if step is None:
            raise StepNotFoundError(step_id)
        return step

    def list_by_plan(self, plan_id: int) -> list[Step]:
        return self._repository.list_by_plan(plan_id)

    def update(self, step_id: int, replacement: Step) -> Step:
        current = self.get(step_id)
        updated = replace(
            replacement,
            id=current.id,
            plan_id=current.plan_id,
            created_at=current.created_at,
            updated_at=datetime.now(UTC),
            deleted_at=current.deleted_at,
        )
        return self._repository.update(updated)

    def delete(self, step_id: int) -> None:
        if not self._repository.delete(step_id):
            raise StepNotFoundError(step_id)
