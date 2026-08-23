from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DocumentCategory = Literal[
    "profile",
    "skills",
    "education",
    "experience",
    "certifications",
    "project",
]


class ProfileDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    category: DocumentCategory
    source: str
    title: str
    content: str
    evidence_level: str | None = None
    evidence_levels: list[str] = Field(default_factory=list)
    similarity: float | None = None


class EvidenceChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    source: str
    category: DocumentCategory
    title: str
    project_id: str | None = None
    evidence_level: str | None = None
    text: str
    similarity: float | None = None


class CandidateProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: ProfileDocument
    skills: ProfileDocument
    experience: ProfileDocument
    education: ProfileDocument
    certifications: ProfileDocument
    projects: list[ProfileDocument] = Field(default_factory=list)
