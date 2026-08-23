from pathlib import Path
from types import SimpleNamespace

from app.config import Settings
from app.infrastructure.rag.chunking import MarkdownProfileChunker
from app.infrastructure.rag.embeddings import OpenAIEmbeddingProvider
from app.infrastructure.rag.vector_store import JsonVectorStore
from app.models.profile import EvidenceChunk, ProfileDocument
from app.models.job_analysis import JobAnalysisRequest
from app.models.llm_job_analysis import LLMJobAnalysisOutput
from app.services.jobs.analysis import JobAnalysisService
from app.services.profile.evidence import RagCandidateEvidenceProvider
from app.services.profile.repository import FileCandidateProfileRepository


def test_markdown_chunking_preserves_metadata_and_source() -> None:
    document = ProfileDocument(
        id="dentalclinic-microservices",
        category="project",
        source="data/profile/projects/dentalclinic-microservices.md",
        title="DentalClinic-Microservices",
        content="# DentalClinic-Microservices\n\n## Technologies\n\n.NET 9, C#, ASP.NET Core.",
        evidence_level="Tier 1 project",
    )

    chunks = MarkdownProfileChunker(max_characters=200).chunk_document(document)

    assert len(chunks) == 1
    assert chunks[0].source == document.source
    assert chunks[0].project_id == document.id
    assert chunks[0].title == "Technologies"
    assert ".NET 9, C#, ASP.NET Core." in chunks[0].text
    assert chunks[0].evidence_level == document.evidence_level


def test_empty_markdown_document_produces_no_chunks() -> None:
    document = ProfileDocument(
        id="empty",
        category="profile",
        source="data/profile/profile.md",
        title="Empty",
        content="",
    )

    assert MarkdownProfileChunker().chunk_document(document) == []


def test_json_vector_store_indexes_and_returns_top_k(tmp_path: Path) -> None:
    chunks = [
        EvidenceChunk(
            chunk_id="one",
            source="data/profile/skills.md",
            category="skills",
            title="Tier 1",
            text="C# and .NET",
        ),
        EvidenceChunk(
            chunk_id="two",
            source="data/profile/projects/portfolio.md",
            category="project",
            title="Portfolio",
            project_id="portfolio",
            text="Next.js and TypeScript",
        ),
    ]
    store = JsonVectorStore(tmp_path / "index.json")

    assert store.rebuild(chunks, [[1.0, 0.0], [0.0, 1.0]]) == 2
    results = store.search([1.0, 0.0], top_k=1, threshold=0.5)

    assert len(results) == 1
    assert results[0].chunk_id == "one"
    assert results[0].source == "data/profile/skills.md"
    assert results[0].similarity == 1.0


def test_rag_provider_returns_only_indexed_structured_evidence() -> None:
    chunk = EvidenceChunk(
        chunk_id="skills:1:0",
        source="data/profile/skills.md",
        category="skills",
        title="Tier 1",
        text="C# · .NET / ASP.NET Core",
        similarity=0.91,
    )

    class FakeEmbeddings:
        def embed(self, texts: list[str]) -> list[list[float]]:
            assert texts == ["backend .NET job"]
            return [[1.0, 0.0]]

    class FakeIndex:
        def search(self, query_vector: list[float], top_k: int, threshold: float) -> list[EvidenceChunk]:
            assert query_vector == [1.0, 0.0]
            assert top_k == 2
            assert threshold == 0.4
            return [chunk]

    provider = RagCandidateEvidenceProvider(FakeEmbeddings(), FakeIndex(), 2, 0.4)
    evidence = provider.get_evidence("backend .NET job")

    assert len(evidence) == 1
    assert evidence[0].source == "data/profile/skills.md"
    assert evidence[0].content == chunk.text
    assert evidence[0].id == chunk.chunk_id


def test_openai_embedding_provider_uses_configured_model() -> None:
    class FakeEmbeddings:
        def create(self, **kwargs: object) -> SimpleNamespace:
            assert kwargs["model"] == "test-embedding-model"
            assert kwargs["input"] == ["C#"]
            return SimpleNamespace(data=[SimpleNamespace(index=0, embedding=[0.1, 0.2])])

    fake_client = SimpleNamespace(embeddings=FakeEmbeddings())
    provider = OpenAIEmbeddingProvider(
        Settings(openai_api_key="test-key", embedding_model="test-embedding-model"),
        client=fake_client,  # type: ignore[arg-type]
    )

    assert provider.embed(["C#"]) == [[0.1, 0.2]]


def test_job_analysis_llm_receives_only_retrieved_evidence(tmp_path: Path) -> None:
    repository = FileCandidateProfileRepository(
        Path(__file__).resolve().parents[3] / "data" / "profile"
    )
    retrieved_chunk = EvidenceChunk(
        chunk_id="skills:1:0",
        source="data/profile/skills.md",
        category="skills",
        title="Tier 1",
        text="C# · .NET / ASP.NET Core",
    )

    class FakeEmbeddings:
        def embed(self, texts: list[str]) -> list[list[float]]:
            return [[1.0]]

    class FakeIndex:
        def search(self, query_vector: list[float], top_k: int, threshold: float) -> list[EvidenceChunk]:
            return [retrieved_chunk]

    evidence_provider = RagCandidateEvidenceProvider(
        FakeEmbeddings(),
        FakeIndex(),
        top_k=8,
        similarity_threshold=0.0,
    )

    class CapturingLLM:
        received_evidence: list[ProfileDocument] = []

        def analyze(
            self,
            job_description: str,
            evidence_documents: list[ProfileDocument],
        ) -> LLMJobAnalysisOutput:
            self.received_evidence = evidence_documents
            return LLMJobAnalysisOutput(
                job_summary="Backend job",
                matched_candidate_claims=[],
                missing_requirements=[],
                analysis="Retrieved evidence only.",
            )

    llm = CapturingLLM()
    response = JobAnalysisService(
        evidence_provider=evidence_provider,
        llm=llm,
        repository=repository,
    ).analyze(
        JobAnalysisRequest(
            job_description=(
                "We need a backend .NET developer to build reliable APIs and maintain "
                "secure web services."
            )
        )
    )

    assert response.status == "analyzed"
    assert len(llm.received_evidence) == 1
    assert llm.received_evidence[0].content == retrieved_chunk.text
    assert llm.received_evidence[0].source == retrieved_chunk.source
