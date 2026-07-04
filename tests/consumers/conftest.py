from collections.abc import Iterator
from unittest.mock import Mock

import pytest


@pytest.fixture
def publisher_mock() -> Mock:
    return Mock()


@pytest.fixture
def scheduler_mock() -> Mock:
    return Mock()


@pytest.fixture
def cache_mock() -> Mock:
    return Mock()


@pytest.fixture
def execution_repository_mock() -> Mock:
    return Mock()


@pytest.fixture
def orchestrator_mock() -> Mock:
    return Mock()


@pytest.fixture
def celery_app_mock() -> Mock:
    return Mock()


@pytest.fixture(autouse=True)
def reset_consumer_mocks() -> Iterator[None]:
    yield