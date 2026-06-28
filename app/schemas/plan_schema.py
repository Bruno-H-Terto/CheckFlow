from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from domain.entities.execution import ExecutionStatus
from domain.entities.step import JsonValue


class PlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default="", max_length=2_000)


class PlanUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default="", max_length=2_000)
    active: bool = True


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    active: bool


class PlanExecutionRequest(BaseModel):
    scheduled_for: datetime | None = None
    variables: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])


class PlanExecutionAccepted(BaseModel):
    event_id: str
    event_type: str
    plan_id: int
    execution_id: str
    occurred_at: datetime


class StepExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    execution_id: str
    step_id: int
    status: ExecutionStatus
    status_code: int | None
    latency_ms: float | None
    assertions: list[dict[str, JsonValue]]
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None


class PlanExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    plan_id: int
    status: ExecutionStatus
    variables: dict[str, JsonValue]
    retry_of: str | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class PlanExecutionDetail(PlanExecutionResponse):
    steps: list[StepExecutionResponse]
