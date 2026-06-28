from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.schemas.plan_schema import (
    PlanCreate,
    PlanExecutionAccepted,
    PlanExecutionRequest,
    PlanResponse,
    PlanUpdate,
    PlanExecutionDetail,
    PlanExecutionResponse,
    StepExecutionResponse,
)
from app.ports.execution_repository import ExecutionRepository
from domain.entities.execution import ExecutionStatus
from domain.events import ExecutionControl
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


def get_execution_repository(request: Request) -> ExecutionRepository:
    repository = cast(
        ExecutionRepository | None, request.app.state.execution_repository
    )
    if repository is None:
        raise HTTPException(
            status_code=503, detail="Execution history is not configured"
        )
    return repository


ExecutionRepositoryDependency = Annotated[
    ExecutionRepository, Depends(get_execution_repository)
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
        event = scheduler.schedule(plan_id, request.scheduled_for, request.variables)
    except PlanNotFoundError as error:
        raise _not_found(error) from error
    return PlanExecutionAccepted(
        event_id=event.event_id,
        event_type=event.event_type,
        plan_id=event.plan_id,
        execution_id=event.execution_id,
        occurred_at=event.occurred_at,
    )


@router.get(
    "/{plan_id}/executions",
    response_model=list[PlanExecutionResponse],
    summary="Listar histórico de execuções",
)
def list_executions(
    plan_id: int,
    service: PlanServiceDependency,
    executions: ExecutionRepositoryDependency,
) -> list[PlanExecutionResponse]:
    try:
        service.get(plan_id)
    except PlanNotFoundError as error:
        raise _not_found(error) from error
    return [
        PlanExecutionResponse.model_validate(item)
        for item in executions.list_by_plan(plan_id)
    ]


@router.get(
    "/{plan_id}/executions/{execution_id}",
    response_model=PlanExecutionDetail,
    summary="Consultar resultado da execução",
)
def get_execution(
    plan_id: int, execution_id: str, executions: ExecutionRepositoryDependency
) -> PlanExecutionDetail:
    execution = executions.get(execution_id)
    if execution is None or execution.plan_id != plan_id:
        raise HTTPException(
            status_code=404, detail=f"Execution {execution_id} was not found"
        )
    steps = [
        StepExecutionResponse.model_validate(item)
        for item in executions.list_steps(execution_id)
    ]
    return PlanExecutionDetail(
        **PlanExecutionResponse.model_validate(execution).model_dump(), steps=steps
    )


@router.post(
    "/{plan_id}/executions/{execution_id}/cancel",
    status_code=202,
    summary="Cancelar execução",
)
def cancel_execution(
    plan_id: int,
    execution_id: str,
    scheduler: PlanSchedulerDependency,
    executions: ExecutionRepositoryDependency,
) -> dict[str, str]:
    execution = executions.get(execution_id)
    if execution is None or execution.plan_id != plan_id:
        raise HTTPException(
            status_code=404, detail=f"Execution {execution_id} was not found"
        )
    if execution.status in {
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
    }:
        raise HTTPException(
            status_code=409, detail=f"Execution is already {execution.status.value}"
        )
    event = scheduler.control(plan_id, execution_id, ExecutionControl.STOP)
    return {
        "event_id": event.event_id,
        "execution_id": execution_id,
        "status": "cancellation_requested",
    }


@router.post(
    "/{plan_id}/executions/{execution_id}/retry",
    response_model=PlanExecutionAccepted,
    status_code=202,
    summary="Reexecutar execução com falha",
)
def retry_execution(
    plan_id: int,
    execution_id: str,
    scheduler: PlanSchedulerDependency,
    executions: ExecutionRepositoryDependency,
) -> PlanExecutionAccepted:
    previous = executions.get(execution_id)
    if previous is None or previous.plan_id != plan_id:
        raise HTTPException(
            status_code=404, detail=f"Execution {execution_id} was not found"
        )
    if previous.status not in {ExecutionStatus.FAILED, ExecutionStatus.CANCELLED}:
        raise HTTPException(
            status_code=409, detail="Only failed or cancelled executions can be retried"
        )
    event = scheduler.schedule(
        plan_id, variables=previous.variables, retry_of=execution_id
    )
    return PlanExecutionAccepted(
        event_id=event.event_id,
        event_type=event.event_type,
        plan_id=event.plan_id,
        execution_id=event.execution_id,
        occurred_at=event.occurred_at,
    )
