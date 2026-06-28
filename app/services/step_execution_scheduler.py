from app.ports.event_publisher import EventPublisher
from domain.events import StepExecutionRequested


class StepExecutionScheduler:
    topic = "checkflow.step-executions"

    def __init__(self, publisher: EventPublisher) -> None:
        self._publisher = publisher

    def schedule(self, step_id: int) -> StepExecutionRequested:
        event = StepExecutionRequested(step_id=step_id)
        self._publisher.publish(
            topic=self.topic,
            key=str(step_id),
            payload=event.to_payload(),
        )
        return event
