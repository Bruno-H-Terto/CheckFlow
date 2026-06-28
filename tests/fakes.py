from dataclasses import replace

from domain.entities.flow_validator import Plan
from domain.entities.step import Step
from domain.entities.execution import ExecutionStatus, PlanExecution, StepExecution
from domain.entities.step import JsonValue


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

    def reorder(self, plan_id: int, positions: dict[int, int]) -> list[Step]:
        steps = self._steps.get(plan_id, {})
        if set(positions) != set(steps):
            raise ValueError("Reorder must include every step in the plan")
        if set(positions.values()) != set(range(1, len(steps) + 1)):
            raise ValueError("Sequences must be unique and contiguous from 1")
        for step_id, sequence in positions.items():
            steps[step_id] = replace(steps[step_id], sequence=sequence)
        return self.list_by_plan(plan_id)


class InMemoryExecutionRepository:
    def __init__(self) -> None:
        self.executions: dict[str, PlanExecution] = {}
        self.step_executions: dict[str, list[StepExecution]] = {}

    def create(self, execution: PlanExecution) -> PlanExecution:
        self.executions[execution.id] = execution
        return execution

    def get(self, execution_id: str) -> PlanExecution | None:
        return self.executions.get(execution_id)

    def list_by_plan(self, plan_id: int) -> list[PlanExecution]:
        return [item for item in self.executions.values() if item.plan_id == plan_id]

    def set_plan_status(
        self, execution_id: str, status: ExecutionStatus, error: str | None = None
    ) -> None:
        current = self.executions[execution_id]
        self.executions[execution_id] = replace(current, status=status, error=error)

    def merge_variables(
        self, execution_id: str, variables: dict[str, JsonValue]
    ) -> None:
        current = self.executions[execution_id]
        self.executions[execution_id] = replace(
            current, variables={**current.variables, **variables}
        )

    def start_step(self, execution_id: str, step_id: int) -> None:
        items = self.step_executions.setdefault(execution_id, [])
        items.append(
            StepExecution(
                id=len(items) + 1,
                execution_id=execution_id,
                step_id=step_id,
                status=ExecutionStatus.RUNNING,
            )
        )

    def finish_step(
        self,
        execution_id: str,
        step_id: int,
        status: ExecutionStatus,
        *,
        status_code: int | None = None,
        latency_ms: float | None = None,
        assertions: list[dict[str, JsonValue]] | None = None,
        error: str | None = None,
    ) -> None:
        items = self.step_executions[execution_id]
        current = items[-1]
        items[-1] = replace(
            current,
            status=status,
            status_code=status_code,
            latency_ms=latency_ms,
            assertions=assertions or [],
            error=error,
        )

    def list_steps(self, execution_id: str) -> list[StepExecution]:
        return self.step_executions.get(execution_id, [])

    def close(self) -> None:
        pass
