from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.schemas.plan_schema import (
    PlanCreate,
    PlanExecutionAccepted,
    PlanExecutionRequest,
    PlanResponse,
    PlanUpdate,
)
from app.services import PlanExecutionScheduler, PlanNotFoundError, PlanService

router = APIRouter(prefix="/plans", tags=["plans"])


def get_plan_service(request: Request) -> PlanService:
    return cast(PlanService, request.app.state.plan_service)


PlanServiceDependency = Annotated[PlanService, Depends(get_plan_service)]


def get_plan_execution_scheduler(request: Request) -> PlanExecutionScheduler:
    scheduler = cast(
        PlanExecutionScheduler | None,
        request.app.state.plan_execution_scheduler,
    )
    if scheduler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plan execution publisher is not configured",
        )
    return scheduler


PlanSchedulerDependency = Annotated[
    PlanExecutionScheduler,
    Depends(get_plan_execution_scheduler),
]


def _not_found(error: PlanNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.post(
    "",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar plano",
)
def create_plan(payload: PlanCreate, service: PlanServiceDependency) -> PlanResponse:
    plan = service.create(payload.name, payload.description)

    return PlanResponse.model_validate(plan)


@router.get("", response_model=list[PlanResponse], summary="Listar planos")
def list_plans(service: PlanServiceDependency) -> list[PlanResponse]:
    return [PlanResponse.model_validate(plan) for plan in service.list()]


@router.get("/{plan_id}", response_model=PlanResponse, summary="Consultar plano")
def get_plan(plan_id: int, service: PlanServiceDependency) -> PlanResponse:
    try:
        return PlanResponse.model_validate(service.get(plan_id))
    except PlanNotFoundError as error:
        raise _not_found(error) from error


@router.put("/{plan_id}", response_model=PlanResponse, summary="Atualizar plano")
def update_plan(
    plan_id: int,
    payload: PlanUpdate,
    service: PlanServiceDependency,
) -> PlanResponse:
    try:
        plan = service.update(
            plan_id,
            name=payload.name,
            description=payload.description,
            active=payload.active,
        )

        return PlanResponse.model_validate(plan)
    except PlanNotFoundError as error:
        raise _not_found(error) from error


@router.delete(
    "/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover plano",
)
def delete_plan(plan_id: int, service: PlanServiceDependency) -> Response:
    try:
        service.delete(plan_id)
    except PlanNotFoundError as error:
        raise _not_found(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{plan_id}/executions",
    response_model=PlanExecutionAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Executar ou agendar plano",
    description=(
        "Executa o primeiro step e libera os próximos automaticamente, em ordem, "
        "quando o step anterior termina com sucesso."
    ),
)
def schedule_plan_execution(
    plan_id: int,
    scheduler: PlanSchedulerDependency,
    service: PlanServiceDependency,
    payload: PlanExecutionRequest | None = None,
) -> PlanExecutionAccepted:
    try:
        service.get(plan_id)
        request = payload or PlanExecutionRequest()
        event = scheduler.schedule(plan_id, request.scheduled_for)
    except PlanNotFoundError as error:
        raise _not_found(error) from error
    return PlanExecutionAccepted(
        event_id=event.event_id,
        event_type=event.event_type,
        plan_id=event.plan_id,
        execution_id=event.execution_id,
        occurred_at=event.occurred_at,
    )
