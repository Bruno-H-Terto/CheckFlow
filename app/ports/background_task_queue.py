from typing import Protocol


class BackgroundTaskQueue(Protocol):
    def enqueue_step(
        self,
        plan_id: int,
        step_id: int,
        execution_id: str,
    ) -> None: ...
