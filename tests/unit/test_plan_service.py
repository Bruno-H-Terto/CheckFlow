import pytest

from app.services import PlanNotFoundError, PlanService
from tests.fakes import InMemoryPlanRepository


@pytest.fixture
def service() -> PlanService:
    return PlanService(InMemoryPlanRepository())


def test_creates_and_lists_plan(service: PlanService) -> None:
    created = service.create("Checkout", "Validates the checkout flow")

    assert created.id == 1
    assert service.list() == [created]


def test_updates_plan(service: PlanService) -> None:
    created = service.create("Old name")

    updated = service.update(
        1,
        name="New name",
        description="Updated",
        active=False,
    )

    assert updated.id == created.id
    assert updated.name == "New name"
    assert updated.active is False


def test_deletes_plan(service: PlanService) -> None:
    service.create("Disposable")

    service.delete(1)

    assert service.list() == []


def test_raises_when_plan_does_not_exist(service: PlanService) -> None:
    with pytest.raises(PlanNotFoundError, match="Plan 99 was not found"):
        service.get(99)

    with pytest.raises(PlanNotFoundError):
        service.delete(99)
