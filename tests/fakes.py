from dataclasses import replace

from domain.entities.flow_validator import Plan


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
