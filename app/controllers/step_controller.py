from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.schemas.step_schema import (
    StepCreate,
    StepExecutionAccepted,
    StepExecutionRequest,
    StepResponse,
    StepUpdate,
)
from app.services import (
    PlanNotFoundError,
    PlanService,
    StepExecutionScheduler,
    StepNotFoundError,
    StepService,
)

router = APIRouter(tags=["steps"])


def get_step_service(request: Request) -> StepService:
    return cast(StepService, request.app.state.step_service)


def get_plan_service(request: Request) -> PlanService:
    return cast(PlanService, request.app.state.plan_service)


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


StepServiceDependency = Annotated[StepService, Depends(get_step_service)]
PlanServiceDependency = Annotated[PlanService, Depends(get_plan_service)]
StepSchedulerDependency = Annotated[
    StepExecutionScheduler,
    Depends(get_step_execution_scheduler),
]


def _not_found(error: StepNotFoundError | PlanNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.post(
    "/plans/{plan_id}/steps",
    response_model=StepResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_step(
    plan_id: int,
    payload: StepCreate,
    step_service: StepServiceDependency,
    plan_service: PlanServiceDependency,
) -> StepResponse:
    try:
        plan_service.get(plan_id)
        step = step_service.create(payload.to_entity(plan_id))
        return StepResponse.model_validate(step)
    except PlanNotFoundError as error:
        raise _not_found(error) from error


@router.get("/plans/{plan_id}/steps", response_model=list[StepResponse])
def list_steps(
    plan_id: int,
    step_service: StepServiceDependency,
    plan_service: PlanServiceDependency,
) -> list[StepResponse]:
    try:
        plan_service.get(plan_id)
    except PlanNotFoundError as error:
        raise _not_found(error) from error
    return [
        StepResponse.model_validate(step) for step in step_service.list_by_plan(plan_id)
    ]


@router.get("/steps/{step_id}", response_model=StepResponse)
def get_step(step_id: int, service: StepServiceDependency) -> StepResponse:
    try:
        return StepResponse.model_validate(service.get(step_id))
    except StepNotFoundError as error:
        raise _not_found(error) from error


@router.put("/steps/{step_id}", response_model=StepResponse)
def update_step(
    step_id: int,
    payload: StepUpdate,
    service: StepServiceDependency,
) -> StepResponse:
    try:
        current = service.get(step_id)
        updated = service.update(step_id, payload.to_entity(current.plan_id))
        return StepResponse.model_validate(updated)
    except StepNotFoundError as error:
        raise _not_found(error) from error


@router.delete("/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_step(step_id: int, service: StepServiceDependency) -> Response:
    try:
        service.delete(step_id)
    except StepNotFoundError as error:
        raise _not_found(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/steps/{step_id}/executions",
    response_model=StepExecutionAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def schedule_step_execution(
    step_id: int,
    scheduler: StepSchedulerDependency,
    step_service: StepServiceDependency,
    payload: StepExecutionRequest | None = None,
) -> StepExecutionAccepted:
    try:
        step_service.get(step_id)
        request = payload or StepExecutionRequest()
        event = scheduler.schedule(step_id, request.scheduled_for)
    except StepNotFoundError as error:
        raise _not_found(error) from error
    return StepExecutionAccepted(
        event_id=event.event_id,
        event_type=event.event_type,
        step_id=event.step_id,
        execution_id=event.execution_id,
        occurred_at=event.occurred_at,
    )
