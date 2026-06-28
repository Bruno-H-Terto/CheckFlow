
from dataclasses import replace

from domain.entities.flow_validator import Plan
from domain.entities.step import Step


class InMemoryPlanRepository:
    def __init__(self) -> None:
        self._plans: dict[int, Plan] = {}
        self._next_id = 1

    def add(self, plan: Plan) -> Plan:
        saved = replace(plan, id=self._next_id)
        self._plans[self._next_id] = saved
        self._next_id += 1
        return saved

    def get(self, plan_id: int) -> Plan | None:
        return self._plans.get(plan_id)

    def list(self) -> list[Plan]:
        return list(self._plans.values())

    def update(self, plan: Plan) -> Plan:
        if plan.id is None:
            raise ValueError("Plan must have an id")
        self._plans[plan.id] = plan
        return plan

    def delete(self, plan_id: int) -> bool:
        return self._plans.pop(plan_id, None) is not None


class InMemoryStepRepository:
    def __init__(self) -> None:
        self._steps: dict[int, dict[int, Step]] = {}
        self._next_id = 1

    def add(self, plan_id: int, step: Step) -> Step:
        saved = step.with_id(self._next_id)
        self._steps.setdefault(plan_id, {})[self._next_id] = saved
        self._next_id += 1
        
        return saved

    def get(self, plan_id: int, step_id: int) -> Step | None:
        return self._steps.get(plan_id, {}).get(step_id)

    def list_by_plan(self, plan_id: int) -> list[Step]:
        response: list[Step] = []
        for _, steps in self._steps.items():
            response.extend(steps.values())

        return sorted(
            (step for step in response if step.plan_id == plan_id),
            key=lambda step: step.sequence,
        )


    def update(self, plan_id: int, step: Step) -> Step:
        if step.id is None:
            raise ValueError("Step must have an id")

        if plan_id not in self._steps or step.id not in self._steps[plan_id]:
            raise KeyError(f"Step {step.id} not found in plan {plan_id}")

        self._steps[plan_id][step.id] = step

        return step

    def delete(self, plan_id: int, step_id: int) -> bool:
        steps = self._steps.get(plan_id, None)

        if not steps:
            return False

        deleted = steps.pop(step_id, None)

        return deleted is not None
