from datetime import UTC, datetime

from app.ports.background_task_queue import BackgroundTaskQueue
from app.ports.event_publisher import EventPublisher
from app.ports.step_repository import StepRepository
from domain.entities.step import JsonValue, Step


class PlanExecutionOrchestrator:
    topic = "checkflow.execution-events"

    def __init__(
        self,
        steps: StepRepository,
        tasks: BackgroundTaskQueue,
        publisher: EventPublisher,
    ) -> None:
        self._steps = steps
        self._tasks = tasks
        self._publisher = publisher

    def start(self, plan_id: int, execution_id: str) -> None:
        steps = self._active_steps(plan_id)
        if not steps:
            self._notify("completed", plan_id, execution_id, {"total_steps": 0})
            return
        self._notify_progress("started", plan_id, execution_id, steps[0], 0, len(steps))
        self._enqueue(steps[0], execution_id)

    def step_completed(
        self,
        plan_id: int,
        execution_id: str,
        step_id: int,
    ) -> None:
        steps = self._active_steps(plan_id)
        position = next(
            (index for index, step in enumerate(steps) if step.id == step_id),
            None,
        )
        if position is None:
            raise ValueError(f"Step {step_id} is not part of plan {plan_id}")
        next_position = position + 1
        if next_position >= len(steps):
            self._notify(
                "completed",
                plan_id,
                execution_id,
                {"completed_steps": len(steps), "total_steps": len(steps)},
            )
            return
        next_step = steps[next_position]
        self._notify_progress(
            "progressed",
            plan_id,
            execution_id,
            next_step,
            next_position,
            len(steps),
        )
        self._enqueue(next_step, execution_id)

    def step_failed(
        self,
        plan_id: int,
        execution_id: str,
        step_id: int,
        error: str,
    ) -> None:
        self._notify(
            "failed",
            plan_id,
            execution_id,
            {"step_id": step_id, "error": error},
        )

    def _enqueue(self, step: Step, execution_id: str) -> None:
        if step.id is None:
            raise ValueError("A persisted step is required for execution")
        self._tasks.enqueue_step(step.plan_id, step.id, execution_id)

    def _active_steps(self, plan_id: int) -> list[Step]:
        return [step for step in self._steps.list_by_plan(plan_id) if step.active]

    def _notify_progress(
        self,
        state: str,
        plan_id: int,
        execution_id: str,
        step: Step,
        completed_steps: int,
        total_steps: int,
    ) -> None:
        self._notify(
            state,
            plan_id,
            execution_id,
            {
                "current_step_id": step.id,
                "current_step_name": step.name,
                "completed_steps": completed_steps,
                "total_steps": total_steps,
            },
        )

    def _notify(
        self,
        state: str,
        plan_id: int,
        execution_id: str,
        extra: dict[str, JsonValue],
    ) -> None:
        payload: dict[str, JsonValue] = {
            "event_type": f"plan.execution.{state}.v1",
            "plan_id": plan_id,
            "execution_id": execution_id,
            "occurred_at": datetime.now(UTC).isoformat(),
            **extra,
        }
        self._publisher.publish(self.topic, execution_id, payload)
