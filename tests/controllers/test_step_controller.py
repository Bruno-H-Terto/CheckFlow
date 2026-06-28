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

    fetched = request(client, "GET", "/plans/1/steps/1")
    assert fetched.status_code == 200

    updated = request(client, "PUT", "/plans/1/steps/1", step_payload("Submit order"))
    assert updated.status_code == 200
    assert updated.json()["name"] == "Submit order"

    deleted = request(client, "DELETE", "/plans/1/steps/1")
    assert deleted.status_code == 204
    assert request(client, "GET", "/plans/1/steps/1").status_code == 404


def test_rejects_unknown_plan(client: TestClient) -> None:
    assert request(client, "POST", "/plans/99/steps", step_payload()).status_code == 404


def test_assigns_sequence_and_reorders_all_steps(client: TestClient) -> None:
    request(client, "POST", "/plans", {"name": "Order flow"})
    first_payload = step_payload("First")
    first_payload.pop("sequence")
    second_payload = step_payload("Second")
    second_payload.pop("sequence")
    first = request(client, "POST", "/plans/1/steps", first_payload).json()
    second = request(client, "POST", "/plans/1/steps", second_payload).json()
    assert [first["sequence"], second["sequence"]] == [1, 2]

    reordered = request(
        client,
        "PATCH",
        "/plans/1/steps/reorder",
        {
            "steps": [
                {"step_id": first["id"], "sequence": 2},
                {"step_id": second["id"], "sequence": 1},
            ]
        },
    )
    assert reordered.status_code == 200
    assert [item["name"] for item in reordered.json()] == ["Second", "First"]
