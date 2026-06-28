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
        if step.sequence == 0:
            current = self._repository.list_by_plan(step.plan_id)
            step = replace(
                step, sequence=max((item.sequence for item in current), default=0) + 1
            )
        return self._repository.add(step.plan_id, step)

    def get(self, plan_id: int, step_id: int) -> Step:
        step = self._repository.get(plan_id, step_id)
        if step is None:
            raise StepNotFoundError(step_id)

        return step

    def list_by_plan(self, plan_id: int) -> list[Step]:
        return self._repository.list_by_plan(plan_id)

    def update(self, plan_id: int, step_id: int, replacement: Step) -> Step:
        current = self.get(plan_id, step_id)

        updated = replace(
            replacement,
            id=current.id,
            plan_id=current.plan_id,
            created_at=current.created_at,
            updated_at=datetime.now(UTC),
            deleted_at=current.deleted_at,
        )

        return self._repository.update(plan_id, updated)

    def delete(self, plan_id: int, step_id: int) -> None:
        if not self._repository.delete(plan_id, step_id):
            raise StepNotFoundError(step_id)

    def reorder(self, plan_id: int, positions: dict[int, int]) -> list[Step]:
        try:
            return self._repository.reorder(plan_id, positions)
        except ValueError:
            raise
