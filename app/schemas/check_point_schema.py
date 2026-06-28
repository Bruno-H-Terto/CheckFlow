from typing import Annotated, Literal

from pydantic import AnyHttpUrl, BaseModel, Field

from domain.entities.step import (
    AssertionOperator,
    AssertionTarget,
    HttpAction,
    HttpMethod,
    JsonValue,
    Step,
    StepAssertion,
)


class HttpActionSchema(BaseModel):
    type: Literal["http"] = "http"
    method: HttpMethod
    url: AnyHttpUrl
    headers: dict[str, str] = Field(default_factory=dict[str, str])
    body: JsonValue = None
    timeout_seconds: float = Field(default=30.0, gt=0, le=300)


class AssertionSchema(BaseModel):
    target: AssertionTarget
    operator: AssertionOperator = AssertionOperator.EQUALS
    expected: JsonValue
    path: str | None = None


class StepCreate(BaseModel):
    checkpoint_id: int
    sequence: Annotated[int, Field(ge=1)]
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default="", max_length=2_000)
    action: HttpActionSchema
    assertions: list[AssertionSchema] = Field(min_length=1)

    def to_entity(self) -> Step:
        action = HttpAction(
            method=self.action.method,
            url=str(self.action.url),
            headers=self.action.headers,
            body=self.action.body,
            timeout_seconds=self.action.timeout_seconds,
        )
        assertions = tuple(
            StepAssertion(
                target=item.target,
                expected=item.expected,
                operator=item.operator,
                path=item.path,
            )
            for item in self.assertions
        )
        return Step(
            checkpoint_id=self.checkpoint_id,
            sequence=self.sequence,
            name=self.name,
            description=self.description,
            action=action,
            assertions=assertions,
        )


class StepUpdate(BaseModel):
    sequence: Annotated[int, Field(ge=1)]
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default="", max_length=2_000)
    action: HttpActionSchema
    assertions: list[AssertionSchema] = Field(min_length=1)
