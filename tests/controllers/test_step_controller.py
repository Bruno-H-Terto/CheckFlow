from collections.abc import Iterator
from typing import cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.main import create_app
from domain.entities.step import JsonValue
from tests.fakes import InMemoryPlanRepository


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
    application = create_app(InMemoryPlanRepository(), publisher)
    with TestClient(application) as test_client:
        yield test_client


def post(client: TestClient, path: str) -> Response:
    return cast(
        Response,
        client.post(path),  # pyright: ignore[reportUnknownMemberType]
    )


def test_schedules_step_execution(
    client: TestClient,
    publisher: SpyEventPublisher,
) -> None:
    response = post(client, "/steps/42/executions")

    assert response.status_code == 202
    assert response.json()["step_id"] == 42
    assert response.json()["event_type"] == "step.execution.requested.v1"
    assert publisher.messages[0][0:2] == ("checkflow.step-executions", "42")


def test_returns_unavailable_without_event_publisher() -> None:
    application = create_app(InMemoryPlanRepository())
    with TestClient(application) as client:
        response = post(client, "/steps/42/executions")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Step execution publisher is not configured"
    }
