from pathlib import Path

from app.config import get_settings
from app.infrastructure.rag.chunking import MarkdownProfileChunker
from app.infrastructure.rag.embeddings import OpenAIEmbeddingProvider
from app.infrastructure.rag.vector_store import JsonVectorStore
from app.services.profile.repository import FileCandidateProfileRepository


def build_profile_index() -> int:
    project_root = Path(__file__).resolve().parents[4]
    settings = get_settings()
    repository = FileCandidateProfileRepository(project_root / "data" / "profile")
    documents = repository.get_candidate_profile()
    all_documents = [
        documents.profile,
        documents.skills,
        documents.experience,
        documents.education,
        documents.certifications,
        *documents.projects,
    ]
    chunks = MarkdownProfileChunker().chunk_documents(all_documents)
    vectors = OpenAIEmbeddingProvider(settings).embed([chunk.text for chunk in chunks])
    index_path = project_root / settings.vector_store_path
    indexed_count = JsonVectorStore(index_path).rebuild(chunks, vectors)
    print(f"Indexed {len(all_documents)} documents into {indexed_count} chunks at {index_path}")
    return indexed_count


if __name__ == "__main__":
    build_profile_index()
