import pytest

from app.schemas.step_schema import StepCreate
from domain.entities.step import (
    ActionResult,
    AssertionOperator,
    AssertionTarget,
    HttpAction,
    HttpMethod,
    Step,
    StepAssertion,
)
from domain.services import StepExecutor


class StubHttpRunner:
    def __init__(self, result: ActionResult) -> None:
        self.result = result
        self.received_action: HttpAction | None = None

    def run(self, action: HttpAction) -> ActionResult:
        self.received_action = action
        return self.result


def test_executes_action_and_evaluates_distributed_system_response() -> None:
    action = HttpAction(HttpMethod.POST, "https://orders.local/orders")
    step = Step(
        id=10,
        plan_id=2,
        sequence=1,
        name="Create order",
        action=action,
        assertions=(
            StepAssertion(AssertionTarget.STATUS_CODE, 201),
            StepAssertion(AssertionTarget.BODY, "accepted", path="data.status"),
            StepAssertion(AssertionTarget.HEADER, "abc-123", path="x-trace-id"),
            StepAssertion(
                AssertionTarget.LATENCY_MS,
                500,
                AssertionOperator.LESS_THAN_OR_EQUAL,
            ),
        ),
    )
    runner = StubHttpRunner(
        ActionResult(
            status_code=201,
            latency_ms=125.5,
            headers={"X-Trace-ID": "abc-123"},
            body={"data": {"status": "accepted"}},
        )
    )

    result = StepExecutor(runner).execute(step)

    assert runner.received_action == action
    assert result.passed is True
    assert all(assertion.passed for assertion in result.assertions)


def test_reports_failed_assertion_without_stopping_evaluation() -> None:
    step = Step(
        plan_id=2,
        sequence=1,
        name="Read order",
        action=HttpAction(HttpMethod.GET, "https://orders.local/orders/42"),
        assertions=(
            StepAssertion(AssertionTarget.STATUS_CODE, 200),
            StepAssertion(AssertionTarget.BODY, "paid", path="status"),
        ),
    )
    runner = StubHttpRunner(ActionResult(503, 20, body={"status": "pending"}))

    result = StepExecutor(runner).execute(step)

    assert result.passed is False
    assert [item.actual for item in result.assertions] == [503, "pending"]
    assert [item.passed for item in result.assertions] == [False, False]


def test_validates_step_and_action_invariants() -> None:
    with pytest.raises(ValueError, match="URL"):
        HttpAction(HttpMethod.GET, "orders.local")

    with pytest.raises(ValueError, match="timeout"):
        HttpAction(HttpMethod.GET, "https://orders.local", timeout_seconds=0)

    with pytest.raises(ValueError, match="requires a path"):
        StepAssertion(AssertionTarget.BODY, "ok")

    with pytest.raises(ValueError, match="at least one assertion"):
        Step(
            plan_id=1,
            sequence=1,
            name="Invalid",
            action=HttpAction(HttpMethod.GET, "https://orders.local"),
            assertions=(),
        )


def test_builds_domain_step_from_api_payload() -> None:
    payload = StepCreate.model_validate(
        {
            "sequence": 2,
            "name": "Query projection",
            "action": {
                "method": "GET",
                "url": "https://query.local/orders/42",
            },
            "assertions": [
                {
                    "target": "body",
                    "path": "status",
                    "expected": "created",
                }
            ],
        }
    )

    step = payload.to_entity(plan_id=5)

    assert step.plan_id == 5
    assert step.action.method == HttpMethod.GET
    assert step.assertions[0].path == "status"
