# pyright: reportFunctionMemberAccess=false, reportUnknownMemberType=false

from adapters.kafka import KafkaEventConsumer, KafkaEventPublisher
from adapters.postgres import PostgresExecutionRepository, PostgresStepRepository
from adapters.redis import RedisJsonCache
from app.services import PlanExecutionOrchestrator
from config.settings import settings
from consumers.celery_app import celery_app
from consumers.tasks import execute_step_task
from domain.entities.step import JsonValue
from domain.entities.execution import ExecutionStatus, PlanExecution
from domain.events import PlanExecutionRequested


class CeleryTaskQueue:
    def enqueue_step(
        self,
        plan_id: int,
        step_id: int,
        execution_id: str,
    ) -> None:
        execute_step_task.apply_async(
            args=[plan_id, step_id, execution_id],
            task_id=f"{execution_id}:{step_id}",
        )


step_repository = PostgresStepRepository.from_url(settings.DATABASE_URL)
publisher = KafkaEventPublisher(settings.KAFKA_BOOTSTRAP_SERVERS)
cache = RedisJsonCache(settings.REDIS_URL, settings.CACHE_TTL_SECONDS)
execution_repository = PostgresExecutionRepository.from_url(settings.DATABASE_URL)
orchestrator = PlanExecutionOrchestrator(
    step_repository,
    CeleryTaskQueue(),
    publisher,
    execution_repository,
)


def handle(payload: dict[str, JsonValue]) -> None:
    event_type = payload.get("event_type")
    execution_id = payload.get("execution_id")
    plan_id = payload.get("plan_id")
    if not isinstance(execution_id, str) or not isinstance(plan_id, int):
        return

    if event_type == "plan.execution.requested.v1":
        orchestrator.start(plan_id, execution_id)
        return

    step_id = payload.get("step_id")
    if event_type == "step.execution.completed.v1" and isinstance(step_id, int):
        orchestrator.step_completed(plan_id, execution_id, step_id)
    elif event_type == "step.execution.failed.v1" and isinstance(step_id, int):
        orchestrator.step_failed(
            plan_id,
            execution_id,
            step_id,
            str(payload.get("error", "Step execution failed")),
        )
    elif event_type == "plan.execution.stop-requested.v1":
        execution_repository.set_plan_status(execution_id, ExecutionStatus.CANCELLED)
        state = cache.get(f"plan-execution:{execution_id}")
        if isinstance(state, dict) and isinstance(state.get("step_id"), int):
            celery_app.control.revoke(
                f"{execution_id}:{state['step_id']}",
                terminate=True,
            )
        publisher.publish(
            "checkflow.execution-events",
            execution_id,
            {
                "event_type": "plan.execution.stopped.v1",
                "plan_id": plan_id,
                "execution_id": execution_id,
            },
        )
    elif event_type == "plan.execution.restart-requested.v1":
        restarted = PlanExecutionRequested(plan_id=plan_id)
        execution_repository.create(
            PlanExecution(
                id=restarted.execution_id, plan_id=plan_id, retry_of=execution_id
            )
        )
        publisher.publish(
            "checkflow.execution-events",
            restarted.execution_id,
            restarted.to_payload(),
        )


def main() -> None:
    KafkaEventConsumer(
        settings.KAFKA_BOOTSTRAP_SERVERS,
        "checkflow-task-dispatcher",
        ["checkflow.execution-events"],
    ).run(handle)


if __name__ == "__main__":
    main()
