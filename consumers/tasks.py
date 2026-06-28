# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUntypedFunctionDecorator=false

from consumers.celery_app import celery_app
from consumers.step_executer import execute_step
from domain.entities.step import JsonValue


@celery_app.task(name="checkflow.execute_step")
def execute_step_task(step_id: int, execution_id: str) -> dict[str, JsonValue]:
    return execute_step(step_id, execution_id)
