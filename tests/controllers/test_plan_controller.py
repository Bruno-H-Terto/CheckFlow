from collections.abc import Iterator
from typing import cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.main import create_app
from tests.fakes import InMemoryPlanRepository


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app(InMemoryPlanRepository())) as test_client:
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
