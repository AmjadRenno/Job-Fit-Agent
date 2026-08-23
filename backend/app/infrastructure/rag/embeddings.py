from typing import Protocol

from openai import OpenAI

from app.config import Settings


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Create one vector for each input text."""


class OpenAIEmbeddingProvider:
    def __init__(self, settings: Settings, client: OpenAI | None = None) -> None:
        if settings.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is required for embeddings.")
        self._client = client or OpenAI(
            api_key=settings.openai_api_key.get_secret_value()
        )
        self._model = settings.embedding_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
