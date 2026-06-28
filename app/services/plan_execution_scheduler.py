from datetime import datetime

from app.ports.event_publisher import EventPublisher
from domain.events import PlanExecutionRequested, PlanExecutionScheduled


type ScheduledExecution = PlanExecutionRequested | PlanExecutionScheduled


class PlanExecutionScheduler:
    topic = "checkflow.execution-events"

    def __init__(self, publisher: EventPublisher) -> None:
        self._publisher = publisher

    def schedule(
        self,
        plan_id: int,
        scheduled_for: datetime | None = None,
    ) -> ScheduledExecution:
        event: ScheduledExecution
        if scheduled_for is None:
            event = PlanExecutionRequested(plan_id=plan_id)
        else:
            event = PlanExecutionScheduled(plan_id=plan_id, scheduled_for=scheduled_for)
        self._publisher.publish(self.topic, event.execution_id, event.to_payload())
        return event
