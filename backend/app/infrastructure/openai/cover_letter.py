from __future__ import annotations

from typing import Protocol

from openai import OpenAI

from app.agent.cover_letter_prompts import (
    COVER_LETTER_CLAIM_INSTRUCTIONS,
    build_cover_letter_claim_input,
)
from app.config import Settings
from app.models.cover_letter import CoverLetterClaimDraft
from app.models.profile import ProfileDocument


class CoverLetterLLM(Protocol):
    def generate_claims(
        self,
        job_title: str,
        company_name: str | None,
        job_description: str,
        evidence_documents: list[ProfileDocument],
        best_match_summary: str | None = None,
        language: str = "en",
        tone: str = "professional",
    ) -> CoverLetterClaimDraft:
        ...


class OpenAICoverLetterLLM:
    def __init__(self, settings: Settings, client: OpenAI | None = None) -> None:
        if settings.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is required for cover-letter generation.")

        self._client = client or OpenAI(api_key=settings.openai_api_key.get_secret_value())
        self._model = settings.openai_model

    def generate_claims(
        self,
        job_title: str,
        company_name: str | None,
        job_description: str,
        evidence_documents: list[ProfileDocument],
        best_match_summary: str | None = None,
        language: str = "en",
        tone: str = "professional",
    ) -> CoverLetterClaimDraft:
        response = self._client.responses.parse(
            model=self._model,
            instructions=COVER_LETTER_CLAIM_INSTRUCTIONS,
            input=build_cover_letter_claim_input(
                job_title,
                company_name,
                job_description,
                [(document.source, document.content) for document in evidence_documents],
                best_match_summary,
                language,
                tone,
            ),
            text_format=CoverLetterClaimDraft,
        )
        if response.output_parsed is None:
            raise ValueError("OpenAI returned no structured cover-letter claim output.")
        return response.output_parsed
