from pathlib import Path

from app.infrastructure.rag.chunking import MarkdownProfileChunker
from app.models.profile import EvidenceChunk
from app.services.profile.evidence import (
    DeterministicCandidateEvidenceProvider,
    RagCandidateEvidenceProvider,
)
from app.services.profile.repository import FileCandidateProfileRepository


class FakeEmbeddings:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0]]


class RelevantOnlyIndex:
    def search(self, query_vector: list[float], top_k: int, threshold: float) -> list[EvidenceChunk]:
        return [
            EvidenceChunk(
                chunk_id="skills:0:0",
                source="data/profile/skills.md",
                category="skills",
                title="Tier 1",
                text="C# · .NET / ASP.NET Core",
                similarity=0.98,
            )
        ][:top_k]


def test_wave_4_retrieval_reduces_evidence_scope_and_preserves_traceability() -> None:
    repository = FileCandidateProfileRepository(
        Path(__file__).resolve().parents[3] / "data" / "profile"
    )
    deterministic = DeterministicCandidateEvidenceProvider(repository)
    full_profile_evidence = deterministic.get_evidence("backend .NET job")
    rag_evidence = RagCandidateEvidenceProvider(
        FakeEmbeddings(),
        RelevantOnlyIndex(),
        top_k=8,
        similarity_threshold=0.5,
    ).get_evidence("backend .NET job")

    assert len(full_profile_evidence) == 15
    assert len(rag_evidence) == 1
    assert rag_evidence[0].source == "data/profile/skills.md"
    assert rag_evidence[0].content == "C# · .NET / ASP.NET Core"
    assert rag_evidence[0].content in repository.get_skills().content


def test_wave_4_chunks_cover_all_canonical_documents() -> None:
    repository = FileCandidateProfileRepository(
        Path(__file__).resolve().parents[3] / "data" / "profile"
    )
    profile = repository.get_candidate_profile()
    documents = [
        profile.profile,
        profile.skills,
        profile.experience,
        profile.education,
        profile.certifications,
        *profile.projects,
    ]

    chunks = MarkdownProfileChunker().chunk_documents(documents)

    assert chunks
    assert {chunk.source for chunk in chunks} == {document.source for document in documents}
