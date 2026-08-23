from pydantic import BaseModel, ConfigDict, Field


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    job_description: str
    expected_relevant_claims: list[str] = Field(default_factory=list)
    expected_missing_requirements: list[str] = Field(default_factory=list)
    forbidden_candidate_claims: list[str] = Field(default_factory=list)


class EvaluationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    grounding: float
    relevance: float
    unsupported_claim_rate: float
    missing_evidence_behavior: float
    claim_validation_rate: float
    raw_claim_count: int
    approved_claim_count: int
    rejected_claim_count: int
    rejected_claims_excluded: bool
    forbidden_claims_present: list[str] = Field(default_factory=list)
    observed_missing_requirements: list[str] = Field(default_factory=list)


class EvaluationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_count: int
    average_grounding: float
    average_relevance: float
    average_unsupported_claim_rate: float
    average_missing_evidence_behavior: float
    average_claim_validation_rate: float
