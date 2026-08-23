from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agent.guardrails import CandidateClaim
from app.models.execution_trace import ExecutionTrace

RequirementType = Literal[
    "required_skill",
    "preferred_skill",
    "experience",
    "education",
    "certification",
    "technology",
    "responsibility",
    "other",
]

RequirementImportance = Literal["required", "preferred", "unknown"]
RequirementStatus = Literal["matched", "partially_matched", "missing", "unknown"]


class BestMatchJobInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str | None = None
    description: str


class BestMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: list[BestMatchJobInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_jobs(self) -> "BestMatchRequest":
        if not self.jobs:
            raise ValueError("At least one job is required for best-match analysis.")
        return self


class JobRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement: str
    requirement_type: RequirementType = "other"
    importance: RequirementImportance = "unknown"
    matched_candidate_claims: list[CandidateClaim] = Field(default_factory=list)
    status: RequirementStatus = "unknown"
    evidence: list[str] = Field(default_factory=list)


class JobMatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    title: str | None = None
    score: float = 0.0
    rank: int = 1
    match_summary: str
    requirement_results: list[JobRequirement] = Field(default_factory=list)
    matched_requirements: list[str] = Field(default_factory=list)
    partial_matches: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    critical_gaps: list[str] = Field(default_factory=list)
    supporting_candidate_evidence: list[str] = Field(default_factory=list)


class BestMatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ranked_jobs: list[JobMatchResult] = Field(default_factory=list)
    best_match: JobMatchResult | None = None
    score: float | None = None
    concise_explanation: str = ""
    important_strengths: list[str] = Field(default_factory=list)
    important_gaps: list[str] = Field(default_factory=list)
    execution_trace: ExecutionTrace | None = None
