from collections.abc import Iterator
from typing import cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.main import create_app
from domain.entities.step import JsonValue
from tests.fakes import InMemoryPlanRepository, InMemoryStepRepository


class SpyEventPublisher:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, dict[str, JsonValue]]] = []

    def publish(
        self,
        topic: str,
        key: str,
        payload: dict[str, JsonValue],
    ) -> None:
        self.messages.append((topic, key, payload))


@pytest.fixture
def publisher() -> SpyEventPublisher:
    return SpyEventPublisher()


@pytest.fixture
def client(publisher: SpyEventPublisher) -> Iterator[TestClient]:
    application = create_app(
        InMemoryPlanRepository(),
        publisher,
        InMemoryStepRepository(),
    )
    with TestClient(application) as test_client:
        yield test_client


def request(
    client: TestClient,
    method: str,
    path: str,
    json: object | None = None,
) -> Response:
    return cast(
        Response,
        client.request(  # pyright: ignore[reportUnknownMemberType]
            method,
            path,
            json=json,
        ),
    )


def test_plan_crud(client: TestClient) -> None:
    created = request(
        client,
        "POST",
        "/plans",
        {"name": "Checkout", "description": "Purchase flow"},
    )
    assert created.status_code == 201
    assert created.json()["id"] == 1

    listed = request(client, "GET", "/plans")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    fetched = request(client, "GET", "/plans/1")
    assert fetched.json()["name"] == "Checkout"

    updated = request(
        client,
        "PUT",
        "/plans/1",
        {"name": "Payment", "description": None, "active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Payment"
    assert updated.json()["active"] is False

    deleted = request(client, "DELETE", "/plans/1")
    assert deleted.status_code == 204

    missing = request(client, "GET", "/plans/1")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Plan 1 was not found"}


def test_validates_plan_payload(client: TestClient) -> None:
    response = request(client, "POST", "/plans", {"name": ""})

    assert response.status_code == 422


def test_schedules_the_whole_plan(
    client: TestClient,
    publisher: SpyEventPublisher,
) -> None:
    request(client, "POST", "/plans", {"name": "Order flow"})

    response = request(client, "POST", "/plans/1/executions", {})

    assert response.status_code == 202
    assert response.json()["plan_id"] == 1
    assert response.json()["event_type"] == "plan.execution.requested.v1"
    assert publisher.messages[0][0:2] == (
        "checkflow.execution-events",
        response.json()["execution_id"],
    )
