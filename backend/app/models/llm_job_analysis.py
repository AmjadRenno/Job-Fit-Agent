from pydantic import BaseModel, ConfigDict, Field

from app.agent.guardrails import CandidateClaim


class LLMJobAnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_summary: str
    matched_candidate_claims: list[CandidateClaim] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    analysis: str