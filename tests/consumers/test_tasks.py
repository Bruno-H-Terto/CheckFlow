from unittest.mock import Mock

from consumers import tasks


def test_execute_step_task_delegates_to_execute_step() -> None:
    execute_step = Mock(return_value={"passed": True})

    tasks.execute_step = execute_step

    result = tasks.execute_step_task.run(1, 2, "execution-123")

    assert result == {"passed": True}
    execute_step.assert_called_once_with(1, 2, "execution-123")