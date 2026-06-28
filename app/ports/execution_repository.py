from typing import Protocol

from domain.entities.execution import ExecutionStatus, PlanExecution, StepExecution
from domain.entities.step import JsonValue


class ExecutionRepository(Protocol):
    def create(self, execution: PlanExecution) -> PlanExecution: ...
    def get(self, execution_id: str) -> PlanExecution | None: ...
    def list_by_plan(self, plan_id: int) -> list[PlanExecution]: ...
    def set_plan_status(
        self, execution_id: str, status: ExecutionStatus, error: str | None = None
    ) -> None: ...
    def merge_variables(
        self, execution_id: str, variables: dict[str, JsonValue]
    ) -> None: ...
    def start_step(self, execution_id: str, step_id: int) -> None: ...
    def finish_step(
        self,
        execution_id: str,
        step_id: int,
        status: ExecutionStatus,
        *,
        status_code: int | None = None,
        latency_ms: float | None = None,
        assertions: list[dict[str, JsonValue]] | None = None,
        error: str | None = None
    ) -> None: ...
    def list_steps(self, execution_id: str) -> list[StepExecution]: ...
    def close(self) -> None: ...
