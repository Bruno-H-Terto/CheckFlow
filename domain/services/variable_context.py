import re
from dataclasses import replace

from domain.entities.step import ActionResult, HttpAction, JsonValue, Step

_VARIABLE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*\}\}")


def render_step(step: Step, variables: dict[str, JsonValue]) -> Step:
    return replace(
        step,
        action=HttpAction(
            method=step.action.method,
            url=str(_render(step.action.url, variables)),
            headers={key: str(_render(value, variables)) for key, value in step.action.headers.items()},
            body=_render(step.action.body, variables),
            timeout_seconds=step.action.timeout_seconds,
        ),
        assertions=tuple(replace(assertion, expected=_render(assertion.expected, variables)) for assertion in step.assertions),
    )


def extract_variables(extracts: dict[str, str], result: ActionResult) -> dict[str, JsonValue]:
    return {name: _extract(source, result) for name, source in extracts.items()}


def _render(value: JsonValue, variables: dict[str, JsonValue]) -> JsonValue:
    if isinstance(value, dict):
        return {key: _render(item, variables) for key, item in value.items()}
    if isinstance(value, list):
        return [_render(item, variables) for item in value]
    if not isinstance(value, str):
        return value
    exact = _VARIABLE.fullmatch(value)
    if exact:
        return _lookup(variables, exact.group(1))
    return _VARIABLE.sub(lambda match: str(_lookup(variables, match.group(1))), value)


def _lookup(variables: dict[str, JsonValue], name: str) -> JsonValue:
    if name not in variables:
        raise ValueError(f"Variable '{name}' is not defined")
    return variables[name]


def _extract(source: str, result: ActionResult) -> JsonValue:
    if source == "status_code":
        return result.status_code
    if source.startswith("header."):
        name = source.removeprefix("header.").lower()
        return {key.lower(): value for key, value in result.headers.items()}.get(name)
    if source.startswith("body."):
        current = result.body
        for part in source.removeprefix("body.").split("."):
            if not isinstance(current, dict) or part not in current:
                raise ValueError(f"Extraction source '{source}' was not found")
            current = current[part]
        return current
    raise ValueError(f"Unsupported extraction source '{source}'")
