from unittest.mock import Mock

from domain.entities.execution import ExecutionStatus
from consumers import task_dispatcher


def test_ignores_payload_without_valid_execution_id() -> None:
    orchestrator = Mock()
    task_dispatcher.orchestrator = orchestrator

    task_dispatcher.handle(
        {
            "event_type": "plan.execution.requested.v1",
            "plan_id": 1,
        }
    )

    orchestrator.start.assert_not_called()


def test_starts_execution_when_plan_execution_is_requested() -> None:
    orchestrator = Mock()
    task_dispatcher.orchestrator = orchestrator

    task_dispatcher.handle(
        {
            "event_type": "plan.execution.requested.v1",
            "plan_id": 1,
            "execution_id": "execution-123",
        }
    )

    orchestrator.start.assert_called_once_with(1, "execution-123")


def test_dispatches_step_completed_event() -> None:
    orchestrator = Mock()
    task_dispatcher.orchestrator = orchestrator

    task_dispatcher.handle(
        {
            "event_type": "step.execution.completed.v1",
            "plan_id": 1,
            "execution_id": "execution-123",
            "step_id": 2,
        }
    )

    orchestrator.step_completed.assert_called_once_with(1, "execution-123", 2)


def test_dispatches_step_failed_event() -> None:
    orchestrator = Mock()
    task_dispatcher.orchestrator = orchestrator

    task_dispatcher.handle(
        {
            "event_type": "step.execution.failed.v1",
            "plan_id": 1,
            "execution_id": "execution-123",
            "step_id": 2,
            "error": "boom",
        }
    )

    orchestrator.step_failed.assert_called_once_with(
        1,
        "execution-123",
        2,
        "boom",
    )


def test_stop_request_cancels_execution_revokes_task_and_publishes_event() -> None:
    execution_repository = Mock()
    cache = Mock()
    celery_app = Mock()
    publisher = Mock()

    cache.get.return_value = {"step_id": 2}

    task_dispatcher.execution_repository = execution_repository
    task_dispatcher.cache = cache
    task_dispatcher.celery_app = celery_app
    task_dispatcher.publisher = publisher

    task_dispatcher.handle(
        {
            "event_type": "plan.execution.stop-requested.v1",
            "plan_id": 1,
            "execution_id": "execution-123",
        }
    )

    execution_repository.set_plan_status.assert_called_once_with(
        "execution-123",
        ExecutionStatus.CANCELLED,
    )
    celery_app.control.revoke.assert_called_once_with(
        "execution-123:2",
        terminate=True,
    )
    publisher.publish.assert_called_once_with(
        "checkflow.execution-events",
        "execution-123",
        {
            "event_type": "plan.execution.stopped.v1",
            "plan_id": 1,
            "execution_id": "execution-123",
        },
    )


def test_restart_request_creates_retry_execution_and_publishes_request() -> None:
    execution_repository = Mock()
    publisher = Mock()

    task_dispatcher.execution_repository = execution_repository
    task_dispatcher.publisher = publisher

    task_dispatcher.handle(
        {
            "event_type": "plan.execution.restart-requested.v1",
            "plan_id": 1,
            "execution_id": "execution-123",
        }
    )

    execution_repository.create.assert_called_once()

    created_execution = execution_repository.create.call_args.args[0]
    assert created_execution.plan_id == 1
    assert created_execution.retry_of == "execution-123"

    publisher.publish.assert_called_once()
    topic, key, payload = publisher.publish.call_args.args

    assert topic == "checkflow.execution-events"
    assert key == created_execution.id
    assert payload["event_type"] == "plan.execution.requested.v1"
    assert payload["plan_id"] == 1