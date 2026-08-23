from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agent.guardrails import CandidateClaim
from app.models.execution_trace import ExecutionTrace


class JobAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_description: str = Field(
        description="Raw job description supplied by the user.",
    )


class JobValidationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_valid: bool
    normalized_text: str | None = None
    error_code: str | None = None
    message: str


class JobAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    summary: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    experience_level: str | None = None
    education: list[str] = Field(default_factory=list)
    location: str | None = None
    matched_candidate_claims: list[CandidateClaim] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    analysis: str | None = None
    grounding_warnings: list[str] = Field(default_factory=list)


class JobAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["invalid", "validated", "analyzed"]
    validation: JobValidationResponse
    analysis: JobAnalysis | None = None
    execution_trace: ExecutionTrace | None = None
