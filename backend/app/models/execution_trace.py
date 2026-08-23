from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TraceStatus = Literal["success", "partial", "failed"]
TraceEventStatus = Literal["success", "failed"]


class TraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: str
    status: TraceEventStatus
    duration_ms: float = Field(ge=0.0)
    detail: str | None = None


class ExecutionTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    operation_id: str
    operation: str
    status: TraceStatus
    events: list[TraceEvent] = Field(default_factory=list)
