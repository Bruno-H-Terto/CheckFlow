import pytest

from app.services import StepNotFoundError, StepService
from domain.entities.step import (
    AssertionTarget,
    HttpAction,
    HttpMethod,
    Step,
    StepAssertion,
)
from tests.fakes import InMemoryStepRepository


def make_step(name: str = "Create order") -> Step:
    return Step(
        plan_id=1,
        sequence=1,
        name=name,
        action=HttpAction(HttpMethod.POST, "https://orders.local/orders"),
        assertions=(StepAssertion(AssertionTarget.STATUS_CODE, 201),),
    )


@pytest.fixture
def service() -> StepService:
    return StepService(InMemoryStepRepository())


def test_creates_updates_and_lists_step(service: StepService) -> None:
    created = service.create(make_step())
    assert created
    assert created.id

    updated = service.update(created.plan_id, created.id, make_step("Submit order"))

    assert updated.name == "Submit order"
    assert updated.plan_id == created.plan_id
    assert service.list_by_plan(1) == [updated]


def test_deletes_step(service: StepService) -> None:
    created = service.create(make_step())

    service.delete(created.plan_id, created.id or 0)

    with pytest.raises(StepNotFoundError):
        service.get(created.plan_id, created.id or 0)


def test_raises_when_deleting_unknown_step(service: StepService) -> None:
    with pytest.raises(StepNotFoundError, match="Step 99 was not found"):
        service.delete(99, 99)
