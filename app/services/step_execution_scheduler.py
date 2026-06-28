from datetime import datetime

from app.ports.event_publisher import EventPublisher
from domain.events import StepExecutionRequested, StepExecutionScheduled

type ScheduledExecution = StepExecutionRequested | StepExecutionScheduled


class StepExecutionScheduler:
    topic = "checkflow.execution.events"

    def __init__(self, publisher: EventPublisher) -> None:
        self._publisher = publisher

    def schedule(
        self,
        step_id: int,
        scheduled_for: datetime | None = None,
    ) -> ScheduledExecution:
        event: ScheduledExecution
        if scheduled_for is None:
            event = StepExecutionRequested(step_id=step_id)
        else:
            event = StepExecutionScheduled(step_id=step_id, scheduled_for=scheduled_for)
        self._publisher.publish(self.topic, event.execution_id, event.to_payload())
        return event
