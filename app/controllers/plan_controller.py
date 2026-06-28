from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.schemas.plan_schema import PlanCreate, PlanResponse, PlanUpdate
from app.services import PlanNotFoundError, PlanService

router = APIRouter(prefix="/plans", tags=["plans"])


def get_plan_service(request: Request) -> PlanService:
    return cast(PlanService, request.app.state.plan_service)


PlanServiceDependency = Annotated[PlanService, Depends(get_plan_service)]


def _not_found(error: PlanNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(payload: PlanCreate, service: PlanServiceDependency) -> PlanResponse:
    plan = service.create(payload.name, payload.description)
    return PlanResponse.model_validate(plan)


@router.get("", response_model=list[PlanResponse])
def list_plans(service: PlanServiceDependency) -> list[PlanResponse]:
    return [PlanResponse.model_validate(plan) for plan in service.list()]


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(plan_id: int, service: PlanServiceDependency) -> PlanResponse:
    try:
        return PlanResponse.model_validate(service.get(plan_id))
    except PlanNotFoundError as error:
        raise _not_found(error) from error


@router.put("/{plan_id}", response_model=PlanResponse)
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


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(plan_id: int, service: PlanServiceDependency) -> Response:
    try:
        service.delete(plan_id)
    except PlanNotFoundError as error:
        raise _not_found(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
