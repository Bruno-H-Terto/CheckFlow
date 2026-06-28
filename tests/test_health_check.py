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
