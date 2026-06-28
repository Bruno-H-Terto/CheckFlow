from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.schemas.step_schema import StepCreate, StepResponse, StepUpdate
from app.services import PlanNotFoundError, PlanService, StepNotFoundError, StepService


router = APIRouter(tags=["steps"])


def get_step_service(request: Request) -> StepService:
    return cast(StepService, request.app.state.step_service)


def get_plan_service(request: Request) -> PlanService:
    return cast(PlanService, request.app.state.plan_service)


StepServiceDependency = Annotated[StepService, Depends(get_step_service)]
PlanServiceDependency = Annotated[PlanService, Depends(get_plan_service)]


def _not_found(error: StepNotFoundError | PlanNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.post(
    "/plans/{plan_id}/steps",
    response_model=StepResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar step no plano",
)
def create_step(
    plan_id: int,
    payload: StepCreate,
    step_service: StepServiceDependency,
    plan_service: PlanServiceDependency,
) -> StepResponse:
    try:
        plan_service.get(plan_id)
        return StepResponse.model_validate(
            step_service.create(payload.to_entity(plan_id))
        )
    except PlanNotFoundError as error:
        raise _not_found(error) from error


@router.get(
    "/plans/{plan_id}/steps",
    response_model=list[StepResponse],
    summary="Listar steps do plano",
)
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
        StepResponse.model_validate(step)
        for step in step_service.list_by_plan(plan_id)
    ]


@router.get(
    "/plans/{plan_id}/steps/{step_id}",
    response_model=StepResponse,
    summary="Consultar step",
)
def get_step(
    plan_id: int, step_id: int, service: StepServiceDependency
) -> StepResponse:
    try:
        return StepResponse.model_validate(service.get(plan_id, step_id))
    except StepNotFoundError as error:
        raise _not_found(error) from error


@router.put(
    "/plans/{plan_id}/steps/{step_id}",
    response_model=StepResponse,
    summary="Atualizar step",
)
def update_step(
    plan_id: int,
    step_id: int,
    payload: StepUpdate,
    service: StepServiceDependency,
) -> StepResponse:
    try:
        current = service.get(plan_id, step_id)
        updated = service.update(plan_id, step_id, payload.to_entity(current.plan_id))
        return StepResponse.model_validate(updated)
    except StepNotFoundError as error:
        raise _not_found(error) from error


@router.delete(
    "/plans/{plan_id}/steps/{step_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover step",
)
def delete_step(plan_id: int, step_id: int, service: StepServiceDependency) -> Response:
    try:
        service.delete(plan_id, step_id)
    except StepNotFoundError as error:
        raise _not_found(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
