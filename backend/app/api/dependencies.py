from pathlib import Path

from fastapi import Depends

from app.agent.tools import SearchCandidateEvidenceTool, ToolRegistry
from app.config import Settings, get_settings
from app.infrastructure.openai.cover_letter import OpenAICoverLetterLLM
from app.infrastructure.openai.tool_calling import OpenAIToolCallingJobAnalysisAgent
from app.infrastructure.rag.embeddings import OpenAIEmbeddingProvider
from app.infrastructure.rag.vector_store import JsonVectorStore
from app.services.jobs.analysis import JobAnalysisService
from app.services.jobs.best_match import BestMatchService
from app.services.jobs.cover_letter import CoverLetterService
from app.services.profile.evidence import RagCandidateEvidenceProvider
from app.services.profile.repository import FileCandidateProfileRepository


def get_job_analysis_service(
    settings: Settings = Depends(get_settings),
) -> JobAnalysisService:
    project_root = Path(__file__).resolve().parents[3]
    repository = FileCandidateProfileRepository(project_root / "data" / "profile")
    evidence_provider = RagCandidateEvidenceProvider(
        embedding_provider=OpenAIEmbeddingProvider(settings),
        evidence_index=JsonVectorStore(project_root / settings.vector_store_path),
        top_k=settings.rag_top_k,
        similarity_threshold=settings.rag_similarity_threshold,
    )
    tool_registry = ToolRegistry(
        [SearchCandidateEvidenceTool(evidence_provider)],
        max_tool_calls=3,
    )
    tool_agent = OpenAIToolCallingJobAnalysisAgent(settings, max_iterations=3)
    return JobAnalysisService(
        evidence_provider=evidence_provider,
        llm=None,
        repository=repository,
        tool_agent=tool_agent,
        tool_registry=tool_registry,
    )


def get_best_match_service(
    settings: Settings = Depends(get_settings),
) -> BestMatchService:
    project_root = Path(__file__).resolve().parents[3]
    repository = FileCandidateProfileRepository(project_root / "data" / "profile")
    evidence_provider = RagCandidateEvidenceProvider(
        embedding_provider=OpenAIEmbeddingProvider(settings),
        evidence_index=JsonVectorStore(project_root / settings.vector_store_path),
        top_k=settings.rag_top_k,
        similarity_threshold=settings.rag_similarity_threshold,
    )
    tool_registry = ToolRegistry(
        [SearchCandidateEvidenceTool(evidence_provider)],
        max_tool_calls=3,
    )
    analysis_service = JobAnalysisService(
        evidence_provider=evidence_provider,
        llm=None,
        repository=repository,
        tool_agent=OpenAIToolCallingJobAnalysisAgent(settings, max_iterations=3),
        tool_registry=tool_registry,
    )
    return BestMatchService(
        evidence_provider=evidence_provider,
        llm=None,
        repository=repository,
        analysis_service=analysis_service,
    )


def get_cover_letter_service(
    settings: Settings = Depends(get_settings),
) -> CoverLetterService:
    project_root = Path(__file__).resolve().parents[3]
    repository = FileCandidateProfileRepository(project_root / "data" / "profile")
    evidence_provider = RagCandidateEvidenceProvider(
        embedding_provider=OpenAIEmbeddingProvider(settings),
        evidence_index=JsonVectorStore(project_root / settings.vector_store_path),
        top_k=settings.rag_top_k,
        similarity_threshold=settings.rag_similarity_threshold,
    )
    llm = OpenAICoverLetterLLM(settings)
    return CoverLetterService(
        evidence_provider=evidence_provider,
        llm=llm,
        repository=repository,
        best_match_service=get_best_match_service(settings),
    )
