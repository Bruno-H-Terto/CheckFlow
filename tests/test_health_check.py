from typing import cast

from httpx import Response
from fastapi.testclient import TestClient


def test_health_check_returns_api_status(client: TestClient) -> None:
    response = cast(
        Response,
        client.get("/health"),  # pyright: ignore[reportUnknownMemberType]
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_documents_public_endpoints(client: TestClient) -> None:
    response = cast(
        Response,
        client.get("/openapi.json"),  # pyright: ignore[reportUnknownMemberType]
    )

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Checkflow API"
    assert "/plans" in schema["paths"]
    assert "/steps/{step_id}/executions" in schema["paths"]
