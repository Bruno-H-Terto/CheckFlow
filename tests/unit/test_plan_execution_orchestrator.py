from dataclasses import replace

from app.services import PlanExecutionOrchestrator
from domain.entities.step import (
    AssertionTarget,
    HttpAction,
    HttpMethod,
    JsonValue,
    Step,
    StepAssertion,
)
from tests.fakes import InMemoryStepRepository


class SpyTaskQueue:
    def __init__(self) -> None:
        self.tasks: list[tuple[int, int, str]] = []

    def enqueue_step(
        self,
        plan_id: int,
        step_id: int,
        execution_id: str,
    ) -> None:
        self.tasks.append((plan_id, step_id, execution_id))


class SpyPublisher:
    def __init__(self) -> None:
        self.messages: list[dict[str, JsonValue]] = []

    def publish(
        self,
        topic: str,
        key: str,
        payload: dict[str, JsonValue],
    ) -> None:
        del topic, key
        self.messages.append(payload)


def make_step(sequence: int, name: str) -> Step:
    return Step(
        plan_id=1,
        sequence=sequence,
        name=name,
        action=HttpAction(HttpMethod.GET, "https://orders.local/health"),
        assertions=(StepAssertion(AssertionTarget.STATUS_CODE, 200),),
    )


def test_runs_plan_steps_sequentially() -> None:
    repository = InMemoryStepRepository()
    first = repository.add(1, make_step(1, "Create order"))
    second = repository.add(1, make_step(2, "Read projection"))
    tasks = SpyTaskQueue()
    publisher = SpyPublisher()
    orchestrator = PlanExecutionOrchestrator(repository, tasks, publisher)

    orchestrator.start(plan_id=1, execution_id="execution-1")

    assert tasks.tasks == [(1, first.id or 0, "execution-1")]
    assert publisher.messages[-1]["event_type"] == "plan.execution.started.v1"

    orchestrator.step_completed(1, "execution-1", first.id or 0)

    assert tasks.tasks[-1] == (1, second.id or 0, "execution-1")
    assert publisher.messages[-1]["completed_steps"] == 1

    orchestrator.step_completed(1, "execution-1", second.id or 0)

    assert publisher.messages[-1]["event_type"] == "plan.execution.completed.v1"
    assert publisher.messages[-1]["completed_steps"] == 2


def test_failure_stops_plan_without_enqueuing_next_step() -> None:
    repository = InMemoryStepRepository()
    first = repository.add(1, make_step(1, "Create order"))
    repository.add(1, make_step(2, "Read projection"))
    tasks = SpyTaskQueue()
    publisher = SpyPublisher()
    orchestrator = PlanExecutionOrchestrator(repository, tasks, publisher)

    orchestrator.start(1, "execution-1")
    orchestrator.step_failed(1, "execution-1", first.id or 0, "HTTP 500")

    assert len(tasks.tasks) == 1
    assert publisher.messages[-1]["event_type"] == "plan.execution.failed.v1"


def test_skips_inactive_steps() -> None:
    repository = InMemoryStepRepository()
    repository.add(1, replace(make_step(1, "Disabled"), active=False))
    active = repository.add(1, make_step(2, "Active"))
    tasks = SpyTaskQueue()
    orchestrator = PlanExecutionOrchestrator(repository, tasks, SpyPublisher())

    orchestrator.start(1, "execution-1")

    assert tasks.tasks == [(1, active.id or 0, "execution-1")]
