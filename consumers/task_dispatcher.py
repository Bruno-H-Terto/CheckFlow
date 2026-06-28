# pyright: reportFunctionMemberAccess=false, reportUnknownMemberType=false

from adapters.kafka import KafkaEventConsumer
from config.settings import settings
from consumers.celery_app import celery_app
from consumers.tasks import execute_step_task
from domain.entities.step import JsonValue
from domain.events import StepExecutionRequested


def handle(payload: dict[str, JsonValue]) -> None:
    event_type = payload.get("event_type")
    execution_id = payload.get("execution_id")
    step_id = payload.get("step_id")
    if not isinstance(execution_id, str) or not isinstance(step_id, int):
        return
    if event_type == "step.execution.requested.v1":
        execute_step_task.apply_async(
            args=[step_id, execution_id],
            task_id=execution_id,
        )
    elif event_type == "step.execution.stop-requested.v1":
        celery_app.control.revoke(execution_id, terminate=True)
    elif event_type == "step.execution.restart-requested.v1":
        event = StepExecutionRequested(step_id=step_id)
        execute_step_task.apply_async(
            args=[step_id, event.execution_id],
            task_id=event.execution_id,
        )


def main() -> None:
    KafkaEventConsumer(
        settings.KAFKA_BOOTSTRAP_SERVERS,
        "checkflow-task-dispatcher",
        ["checkflow.execution-events"],
    ).run(handle)


if __name__ == "__main__":
    main()
