# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from adapters.kafka import KafkaEventConsumer, KafkaEventPublisher
from config.settings import settings
from domain.entities.step import JsonValue
from domain.events import PlanExecutionRequested

publisher = KafkaEventPublisher(settings.KAFKA_BOOTSTRAP_SERVERS)
scheduler = BackgroundScheduler(timezone="UTC")


def handle(payload: dict[str, JsonValue]) -> None:
    if payload.get("event_type") != "plan.execution.scheduled.v1":
        return

    run_at = payload.get("scheduled_for")
    plan_id = payload.get("plan_id")
    execution_id = payload.get("execution_id")

    if not isinstance(run_at, str) or not isinstance(plan_id, int):
        raise ValueError("Scheduled event requires plan_id and scheduled_for")
    if not isinstance(execution_id, str):
        raise ValueError("Scheduled event requires execution_id")

    event = PlanExecutionRequested(plan_id=plan_id, execution_id=execution_id)

    scheduler.add_job(
        publisher.publish,
        trigger="date",
        run_date=datetime.fromisoformat(run_at),
        args=["checkflow.execution-events", execution_id, event.to_payload()],
        id=execution_id,
        replace_existing=True,
    )


def main() -> None:
    scheduler.start()
    try:
        KafkaEventConsumer(
            settings.KAFKA_BOOTSTRAP_SERVERS,
            "checkflow-scheduler",
            ["checkflow.execution-events"],
        ).run(handle)
    finally:
        scheduler.shutdown(wait=True)
        publisher.close()


if __name__ == "__main__":
    main()
