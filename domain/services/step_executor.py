from domain.entities.step import (
    ActionResult,
    ActionRunner,
    AssertionOperator,
    AssertionResult,
    AssertionTarget,
    JsonValue,
    Step,
    StepAssertion,
    StepExecutionResult,
)


class StepExecutor:
    def __init__(self, runner: ActionRunner) -> None:
        self._runner = runner

    def execute(self, step: Step) -> StepExecutionResult:
        action_result = self._runner.run(step.action)
        assertion_results = tuple(
            self._evaluate(assertion, action_result)
            for assertion in step.assertions
        )
        return StepExecutionResult(
            step_id=step.id,
            action_result=action_result,
            assertions=assertion_results,
        )

    def _evaluate(
        self,
        assertion: StepAssertion,
        result: ActionResult,
    ) -> AssertionResult:
        actual = self._actual_value(assertion, result)
        passed = self._compare(actual, assertion.expected, assertion.operator)
        return AssertionResult(assertion=assertion, actual=actual, passed=passed)

    @staticmethod
    def _actual_value(assertion: StepAssertion, result: ActionResult) -> JsonValue:
        if assertion.target == AssertionTarget.STATUS_CODE:
            return result.status_code
        if assertion.target == AssertionTarget.LATENCY_MS:
            return result.latency_ms
        if assertion.target == AssertionTarget.HEADER:
            path = assertion.path or ""
            headers = {name.lower(): value for name, value in result.headers.items()}
            return headers.get(path.lower())
        return StepExecutor._read_body_path(result.body, assertion.path or "")

    @staticmethod
    def _read_body_path(body: JsonValue, path: str) -> JsonValue:
        current = body
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    @staticmethod
    def _compare(
        actual: JsonValue,
        expected: JsonValue,
        operator: AssertionOperator,
    ) -> bool:
        if operator == AssertionOperator.EQUALS:
            return actual == expected
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            return False
        if not isinstance(expected, (int, float)) or isinstance(expected, bool):
            return False
        return actual <= expected
