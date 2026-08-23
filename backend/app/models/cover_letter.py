from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.agent.guardrails import CandidateClaim
from app.models.execution_trace import ExecutionTrace

LanguageCode = Literal["en", "da"]
CoverLetterTone = Literal["professional", "concise", "technical"]


class CoverLetterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    job_title: str
    company_name: str | None = None
    job_description: str = Field(min_length=1)
    language: LanguageCode = "en"
    tone: CoverLetterTone = "professional"

    @field_validator("language", mode="before")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        if isinstance(value, str):
            normalized = value.strip().casefold()
            if normalized in {"en", "english"}:
                return "en"
            if normalized in {"da", "danish"}:
                return "da"
        raise ValueError("Language must be either 'en' or 'da'.")

    @field_validator("tone", mode="before")
    @classmethod
    def normalize_tone(cls, value: str) -> str:
        if isinstance(value, str):
            normalized = value.strip().casefold()
            if normalized in {"professional", "prof", "formal"}:
                return "professional"
            if normalized in {"concise", "short"}:
                return "concise"
            if normalized in {"technical", "tech"}:
                return "technical"
        raise ValueError("Tone must be one of: professional, concise, technical.")

    @model_validator(mode="after")
    def validate_job_description(self) -> "CoverLetterRequest":
        cleaned = " ".join(self.job_description.split())
        if not cleaned:
            raise ValueError("A job description is required for cover-letter generation.")
        if len(cleaned) < 50:
            raise ValueError("The job description must contain at least 50 characters.")
        self.job_description = cleaned
        return self


class CoverLetterClaimDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_claims: list[CandidateClaim] = Field(default_factory=list)
    rejected_candidate_claims: list[CandidateClaim] = Field(default_factory=list)


class CoverLetterResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    job_title: str
    company_name: str | None = None
    language: LanguageCode
    cover_letter: str
    used_candidate_claims: list[CandidateClaim] = Field(default_factory=list)
    grounding_warnings: list[str] = Field(default_factory=list)
    relevant_match_summary: str = ""
    execution_trace: ExecutionTrace | None = None
