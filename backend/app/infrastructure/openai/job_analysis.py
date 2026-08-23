from typing import Protocol

from openai import OpenAI

from app.config import Settings
from app.models.llm_job_analysis import LLMJobAnalysisOutput
from app.models.profile import ProfileDocument
from app.agent.prompts import (
    JOB_ANALYSIS_SYSTEM_INSTRUCTIONS,
    build_job_analysis_input,
)


class JobAnalysisLLM(Protocol):
    def analyze(
        self,
        job_description: str,
        evidence_documents: list[ProfileDocument],
    ) -> LLMJobAnalysisOutput:
        """Return structured analysis grounded in supplied evidence."""


class OpenAIJobAnalysisLLM:
    def __init__(self, settings: Settings, client: OpenAI | None = None) -> None:
        if settings.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is required for LLM-backed job analysis.")

        self._client = client or OpenAI(
            api_key=settings.openai_api_key.get_secret_value()
        )
        self._model = settings.openai_model

    def analyze(
        self,
        job_description: str,
        evidence_documents: list[ProfileDocument],
    ) -> LLMJobAnalysisOutput:
        response = self._client.responses.parse(
            model=self._model,
            instructions=JOB_ANALYSIS_SYSTEM_INSTRUCTIONS,
            input=build_job_analysis_input(
                job_description,
                [(document.source, document.content) for document in evidence_documents],
            ),
            text_format=LLMJobAnalysisOutput,
        )
        if response.output_parsed is None:
            raise ValueError("OpenAI returned no structured job-analysis output.")
        return response.output_parsed