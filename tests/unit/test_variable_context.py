import pytest

from domain.entities.step import (
    ActionResult,
    AssertionTarget,
    HttpAction,
    HttpMethod,
    Step,
    StepAssertion,
)
from domain.services.variable_context import extract_variables, render_step


def _step() -> Step:
    return Step(
        plan_id=1,
        sequence=1,
        name="authorized request",
        action=HttpAction(
            method=HttpMethod.POST,
            url="https://api.local/{{tenant}}",
            headers={"Authorization": "Bearer {{token}}"},
            body={"user_id": "{{user_id}}"},
        ),
        assertions=(
            StepAssertion(
                target=AssertionTarget.STATUS_CODE, expected="{{expected_status}}"
            ),
        ),
    )


def test_renders_dynamic_variables_preserving_exact_value_types() -> None:
    rendered = render_step(
        _step(),
        {"tenant": "acme", "token": "secret", "user_id": 42, "expected_status": 201},
    )
    assert rendered.action.url == "https://api.local/acme"
    assert rendered.action.headers["Authorization"] == "Bearer secret"
    assert rendered.action.body == {"user_id": 42}
    assert rendered.assertions[0].expected == 201


def test_extracts_body_header_and_status_values() -> None:
    result = ActionResult(
        status_code=201,
        latency_ms=2,
        headers={"X-Request-Id": "abc"},
        body={"auth": {"access_token": "jwt"}},
    )
    assert extract_variables(
        {
            "token": "body.auth.access_token",
            "request_id": "header.X-Request-Id",
            "code": "status_code",
        },
        result,
    ) == {"token": "jwt", "request_id": "abc", "code": 201}


def test_rejects_missing_variables_and_extraction_paths() -> None:
    with pytest.raises(ValueError, match="tenant"):
        render_step(_step(), {})
    with pytest.raises(ValueError, match="was not found"):
        extract_variables({"token": "body.access_token"}, ActionResult(200, 1, body={}))
    with pytest.raises(ValueError, match="Unsupported"):
        extract_variables({"token": "cookie.token"}, ActionResult(200, 1))
