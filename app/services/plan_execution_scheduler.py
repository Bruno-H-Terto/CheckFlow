from datetime import datetime

from app.ports.event_publisher import EventPublisher
from app.ports.execution_repository import ExecutionRepository
from domain.entities.execution import PlanExecution
from domain.entities.step import JsonValue
from domain.events import (
    ExecutionControl,
    PlanExecutionControlRequested,
    PlanExecutionRequested,
    PlanExecutionScheduled,
)

type ScheduledExecution = PlanExecutionRequested | PlanExecutionScheduled


class PlanExecutionScheduler:
    topic = "checkflow.execution-events"

    def __init__(
        self, publisher: EventPublisher, executions: ExecutionRepository | None = None
    ) -> None:
        self._publisher = publisher
        self._executions = executions

    def schedule(
        self,
        plan_id: int,
        scheduled_for: datetime | None = None,
        variables: dict[str, JsonValue] | None = None,
        retry_of: str | None = None,
    ) -> ScheduledExecution:
        event: ScheduledExecution
        if scheduled_for is None:
            event = PlanExecutionRequested(plan_id=plan_id)
        else:
            event = PlanExecutionScheduled(plan_id=plan_id, scheduled_for=scheduled_for)
        if self._executions is not None:
            self._executions.create(
                PlanExecution(
                    id=event.execution_id,
                    plan_id=plan_id,
                    variables=variables or {},
                    retry_of=retry_of,
                )
            )
        self._publisher.publish(self.topic, event.execution_id, event.to_payload())
        return event

    def control(
        self, plan_id: int, execution_id: str, command: ExecutionControl
    ) -> PlanExecutionControlRequested:
        event = PlanExecutionControlRequested(
            execution_id=execution_id, plan_id=plan_id, command=command
        )
        self._publisher.publish(self.topic, execution_id, event.to_payload())
        return event
