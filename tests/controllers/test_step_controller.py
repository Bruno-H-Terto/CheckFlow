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


def step_payload(name: str = "Create order") -> dict[str, object]:
    return {
        "sequence": 1,
        "name": name,
        "description": "Calls the order service",
        "action": {
            "method": "POST",
            "url": "https://orders.local/orders",
            "body": {"product_id": 42},
        },
        "assertions": [
            {"target": "status_code", "expected": 201},
            {"target": "body", "path": "status", "expected": "created"},
        ],
    }


def test_step_crud_as_semantic_block_of_plan(client: TestClient) -> None:
    plan = request(client, "POST", "/plans", {"name": "Order flow"})
    assert plan.status_code == 201

    created = request(client, "POST", "/plans/1/steps", step_payload())
    assert created.status_code == 201
    assert created.json()["plan_id"] == 1
    assert created.json()["action"]["method"] == "POST"

    listed = request(client, "GET", "/plans/1/steps")
    assert [item["name"] for item in listed.json()] == ["Create order"]

    fetched = request(client, "GET", "/steps/1")
    assert fetched.status_code == 200

    updated = request(client, "PUT", "/steps/1", step_payload("Submit order"))
    assert updated.status_code == 200
    assert updated.json()["name"] == "Submit order"

    deleted = request(client, "DELETE", "/steps/1")
    assert deleted.status_code == 204
    assert request(client, "GET", "/steps/1").status_code == 404


def test_schedules_existing_step_execution(
    client: TestClient,
    publisher: SpyEventPublisher,
) -> None:
    request(client, "POST", "/plans", {"name": "Order flow"})
    request(client, "POST", "/plans/1/steps", step_payload())

    response = request(client, "POST", "/steps/1/executions")

    assert response.status_code == 202
    assert response.json()["step_id"] == 1
    assert publisher.messages[0][0:2] == ("checkflow.step-executions", "1")


def test_rejects_unknown_plan_and_step(client: TestClient) -> None:
    assert request(client, "POST", "/plans/99/steps", step_payload()).status_code == 404
    assert request(client, "POST", "/steps/99/executions").status_code == 404


def test_returns_unavailable_without_event_publisher() -> None:
    step_repository = InMemoryStepRepository()
    application = create_app(
        InMemoryPlanRepository(),
        step_repository=step_repository,
    )
    with TestClient(application) as client:
        response = request(client, "POST", "/steps/42/executions")

    assert response.status_code == 503
