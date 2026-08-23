from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.profile import DocumentCategory


class SearchCandidateEvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=300)
    category: DocumentCategory | None = None
    project_id: str | None = Field(default=None, max_length=100)
    top_k: int | None = Field(default=5, ge=1, le=10)

    @field_validator("query", "project_id")
    @classmethod
    def reject_unsafe_values(cls, value: str | None) -> str | None:
        if value is None:
            return None
        lowered = value.casefold()
        if any(token in value for token in ("/", "\\", "..")):
            raise ValueError("Path-like tool arguments are not allowed.")
        if any(token in lowered for token in ("secret", "api_key", "environment", "env var", ".env")):
            raise ValueError("Secret or environment access is not allowed.")
        return value


class CandidateEvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    title: str
    category: DocumentCategory
    project_id: str | None = None
    evidence_level: str | None = None
    text: str
    similarity: float | None = None


class SearchCandidateEvidenceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: Literal["search_candidate_evidence"]
    query: str
    evidence: list[CandidateEvidenceItem] = Field(default_factory=list)


class ToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    parameters: dict[str, object]
    strict: bool = True

    def as_openai_tool(self) -> dict[str, object]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "strict": self.strict,
        }
