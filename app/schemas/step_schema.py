from datetime import datetime
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

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
    model_config = ConfigDict(from_attributes=True)

    type: Literal["http"] = "http"
    method: HttpMethod
    url: AnyHttpUrl
    headers: dict[str, str] = Field(default_factory=dict[str, str])
    body: JsonValue = None
    timeout_seconds: float = Field(default=30.0, gt=0, le=300)


class AssertionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target: AssertionTarget
    operator: AssertionOperator = AssertionOperator.EQUALS
    expected: JsonValue
    path: str | None = None


class StepWrite(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default="", max_length=2_000)
    action: HttpActionSchema
    assertions: list[AssertionSchema] = Field(min_length=1)
    extracts: dict[str, str] = Field(default_factory=dict[str, str])
    active: bool = True

    def _to_entity(self, plan_id: int, sequence: int) -> Step:
        return Step(
            plan_id=plan_id,
            sequence=sequence,
            name=self.name,
            description=self.description,
            action=HttpAction(
                method=self.action.method,
                url=str(self.action.url),
                headers=self.action.headers,
                body=self.action.body,
                timeout_seconds=self.action.timeout_seconds,
            ),
            assertions=tuple(
                StepAssertion(
                    target=item.target,
                    expected=item.expected,
                    operator=item.operator,
                    path=item.path,
                )
                for item in self.assertions
            ),
            extracts=self.extracts,
            active=self.active,
        )


class StepCreate(StepWrite):
    sequence: Annotated[int | None, Field(ge=1)] = None

    def to_entity(self, plan_id: int) -> Step:
        return self._to_entity(plan_id, self.sequence or 0)


class StepUpdate(StepWrite):
    sequence: Annotated[int, Field(ge=1)]

    def to_entity(self, plan_id: int) -> Step:
        return self._to_entity(plan_id, self.sequence)


class StepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    sequence: int
    name: str
    description: str | None
    action: HttpActionSchema
    assertions: list[AssertionSchema]
    extracts: dict[str, str]
    created_at: datetime
    updated_at: datetime
    active: bool


class StepPosition(BaseModel):
    step_id: int = Field(gt=0)
    sequence: int = Field(gt=0)


class StepReorder(BaseModel):
    steps: list[StepPosition] = Field(min_length=1)
