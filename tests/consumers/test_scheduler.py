from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from consumers import scheduler


def test_ignores_non_scheduled_events() -> None:
    scheduler_mock = Mock()
    publisher_mock = Mock()

    scheduler.scheduler = scheduler_mock
    scheduler.publisher = publisher_mock

    scheduler.handle({"event_type": "plan.execution.requested.v1"})

    scheduler_mock.add_job.assert_not_called()


def test_adds_job_for_scheduled_execution() -> None:
    scheduler_mock = Mock()
    publisher_mock = Mock()

    scheduler.scheduler = scheduler_mock
    scheduler.publisher = publisher_mock

    scheduler.handle(
        {
            "event_type": "plan.execution.scheduled.v1",
            "plan_id": 1,
            "execution_id": "execution-123",
            "scheduled_for": "2026-06-28T18:00:00+00:00",
        }
    )

    scheduler_mock.add_job.assert_called_once()

    _, kwargs = scheduler_mock.add_job.call_args

    assert kwargs["trigger"] == "date"
    assert kwargs["run_date"] == datetime(2026, 6, 28, 18, 0, tzinfo=UTC)
    assert kwargs["id"] == "execution-123"
    assert kwargs["replace_existing"] is True
    assert kwargs["args"][0] == "checkflow.execution-events"
    assert kwargs["args"][1] == "execution-123"
    assert kwargs["args"][2]["event_type"] == "plan.execution.requested.v1"
    assert kwargs["args"][2]["plan_id"] == 1
    assert kwargs["args"][2]["execution_id"] == "execution-123"


def test_rejects_scheduled_event_without_plan_id() -> None:
    with pytest.raises(ValueError, match="plan_id"):
        scheduler.handle(
            {
                "event_type": "plan.execution.scheduled.v1",
                "execution_id": "execution-123",
                "scheduled_for": "2026-06-28T18:00:00+00:00",
            }
        )


def test_rejects_scheduled_event_without_execution_id() -> None:
    with pytest.raises(ValueError, match="execution_id"):
        scheduler.handle(
            {
                "event_type": "plan.execution.scheduled.v1",
                "plan_id": 1,
                "scheduled_for": "2026-06-28T18:00:00+00:00",
            }
        )