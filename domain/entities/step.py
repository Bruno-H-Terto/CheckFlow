from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | list[JsonValue] | dict[str, JsonValue]


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


@dataclass(frozen=True, slots=True)
class HttpAction:
    method: HttpMethod
    url: str
    headers: dict[str, str] = field(default_factory=dict[str, str])
    body: JsonValue = None
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not self.url.startswith(("http://", "https://")):
            raise ValueError("HTTP action URL must start with http:// or https://")
        if self.timeout_seconds <= 0:
            raise ValueError("HTTP action timeout must be greater than zero")


class AssertionTarget(StrEnum):
    STATUS_CODE = "status_code"
    BODY = "body"
    HEADER = "header"
    LATENCY_MS = "latency_ms"


class AssertionOperator(StrEnum):
    EQUALS = "equals"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"


@dataclass(frozen=True, slots=True)
class StepAssertion:
    target: AssertionTarget
    expected: JsonValue
    operator: AssertionOperator = AssertionOperator.EQUALS
    path: str | None = None

    def __post_init__(self) -> None:
        if self.target in {AssertionTarget.BODY, AssertionTarget.HEADER} and not self.path:
            raise ValueError(f"Assertion target '{self.target}' requires a path")


@dataclass(frozen=True, slots=True)
class Step:
    checkpoint_id: int
    sequence: int
    name: str
    action: HttpAction
    assertions: tuple[StepAssertion, ...]
    id: int | None = None
    description: str | None = ""

    def __post_init__(self) -> None:
        if self.sequence < 1:
            raise ValueError("Step sequence must be greater than zero")
        if not self.assertions:
            raise ValueError("Step must define at least one assertion")


@dataclass(frozen=True, slots=True)
class ActionResult:
    status_code: int
    latency_ms: float
    headers: dict[str, str] = field(default_factory=dict[str, str])
    body: JsonValue = None


class ActionRunner(Protocol):
    def run(self, action: HttpAction) -> ActionResult: ...


@dataclass(frozen=True, slots=True)
class AssertionResult:
    assertion: StepAssertion
    actual: JsonValue
    passed: bool


@dataclass(frozen=True, slots=True)
class StepExecutionResult:
    step_id: int | None
    action_result: ActionResult
    assertions: tuple[AssertionResult, ...]

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.assertions)
