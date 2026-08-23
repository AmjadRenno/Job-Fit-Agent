from typing import Protocol

from app.models.profile import EvidenceChunk, ProfileDocument
from app.services.profile.repository import CandidateProfileRepository


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Create one vector for each input text."""


class CandidateEvidenceIndex(Protocol):
    def search(self, query_vector: list[float], top_k: int, threshold: float) -> list[EvidenceChunk]:
        """Return relevant indexed evidence chunks."""


class CandidateEvidenceProvider(Protocol):
    def get_evidence(self, query: str) -> list[ProfileDocument]:
        """Return candidate evidence relevant to the query."""


class DeterministicCandidateEvidenceProvider:
    def __init__(self, repository: CandidateProfileRepository) -> None:
        self._repository = repository

    def get_evidence(self, query: str) -> list[ProfileDocument]:
        del query
        profile = self._repository.get_candidate_profile()
        return [
            profile.profile,
            profile.skills,
            profile.experience,
            profile.education,
            profile.certifications,
            *profile.projects,
        ]


class RagCandidateEvidenceProvider:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        evidence_index: CandidateEvidenceIndex,
        top_k: int,
        similarity_threshold: float,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._evidence_index = evidence_index
        self._top_k = top_k
        self._similarity_threshold = similarity_threshold

    def get_evidence(self, query: str) -> list[ProfileDocument]:
        vectors = self._embedding_provider.embed([query])
        if not vectors:
            return []
        chunks = self._evidence_index.search(
            vectors[0],
            self._top_k,
            self._similarity_threshold,
        )
        return [
            ProfileDocument(
                id=chunk.chunk_id,
                category=chunk.category,
                source=chunk.source,
                title=chunk.title,
                content=chunk.text,
                evidence_level=chunk.evidence_level,
                similarity=chunk.similarity,
            )
            for chunk in chunks
        ]