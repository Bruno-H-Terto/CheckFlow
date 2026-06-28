from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class PlanExecutionAccepted(BaseModel):
    event_id: str
    event_type: str
    plan_id: int
    execution_id: str
    occurred_at: datetime
