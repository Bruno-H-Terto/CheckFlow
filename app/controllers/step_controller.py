from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.services import StepExecutionScheduler


router = APIRouter(prefix="/steps", tags=["steps"])


class StepExecutionAccepted(BaseModel):
    event_id: str
    event_type: str
    step_id: int
    occurred_at: datetime


def get_step_execution_scheduler(request: Request) -> StepExecutionScheduler:
    scheduler = cast(
        StepExecutionScheduler | None,
        request.app.state.step_execution_scheduler,
    )
    if scheduler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Step execution publisher is not configured",
        )
    return scheduler


StepSchedulerDependency = Annotated[
    StepExecutionScheduler,
    Depends(get_step_execution_scheduler),
]


@router.post(
    "/{step_id}/executions",
    response_model=StepExecutionAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def schedule_step_execution(
    step_id: int,
    scheduler: StepSchedulerDependency,
) -> StepExecutionAccepted:
    event = scheduler.schedule(step_id)
    return StepExecutionAccepted(
        event_id=event.event_id,
        event_type=event.event_type,
        step_id=event.step_id,
        occurred_at=event.occurred_at,
    )
