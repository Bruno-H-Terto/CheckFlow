from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.fakes import InMemoryPlanRepository


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app(InMemoryPlanRepository())) as test_client:
        yield test_client
