import json
import math
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.models.profile import EvidenceChunk


class IndexedChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk: EvidenceChunk
    vector: list[float]


class VectorStore(Protocol):
    def rebuild(self, chunks: list[EvidenceChunk], vectors: list[list[float]]) -> int:
        """Replace the local index and return the indexed chunk count."""

    def search(self, query_vector: list[float], top_k: int, threshold: float) -> list[EvidenceChunk]:
        """Return the highest-scoring chunks above threshold."""


class JsonVectorStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def rebuild(self, chunks: list[EvidenceChunk], vectors: list[list[float]]) -> int:
        if len(chunks) != len(vectors):
            raise ValueError("Each chunk must have one embedding vector.")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            IndexedChunk(chunk=chunk, vector=vector).model_dump(mode="json")
            for chunk, vector in zip(chunks, vectors)
        ]
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return len(payload)

    def search(self, query_vector: list[float], top_k: int, threshold: float) -> list[EvidenceChunk]:
        if top_k <= 0 or not self._path.is_file():
            return []
        indexed = [IndexedChunk.model_validate(item) for item in json.loads(self._path.read_text(encoding="utf-8"))]
        scored = []
        for item in indexed:
            score = _cosine_similarity(query_vector, item.vector)
            if score >= threshold:
                scored.append(item.chunk.model_copy(update={"similarity": score}))
        scored.sort(key=lambda chunk: chunk.similarity or 0.0, reverse=True)
        unique: list[EvidenceChunk] = []
        seen: set[str] = set()
        for chunk in scored:
            if chunk.chunk_id not in seen and chunk.text.strip():
                unique.append(chunk)
                seen.add(chunk.chunk_id)
        return unique[:top_k]


def _cosine_similarity(first: list[float], second: list[float]) -> float:
    if len(first) != len(second) or not first or not second:
        return 0.0
    first_norm = math.sqrt(sum(value * value for value in first))
    second_norm = math.sqrt(sum(value * value for value in second))
    if first_norm == 0 or second_norm == 0:
        return 0.0
    return sum(left * right for left, right in zip(first, second)) / (first_norm * second_norm)
