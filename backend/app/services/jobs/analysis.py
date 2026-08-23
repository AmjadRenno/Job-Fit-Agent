from collections.abc import Callable
import re
from typing import Protocol

from app.agent.guardrails import CandidateClaim, validate_candidate_claim
from app.domain.job_validation import validate_job_description
from app.agent.tools import ToolRegistry
from app.models.job_analysis import (
    JobAnalysis,
    JobAnalysisRequest,
    JobAnalysisResponse,
    JobValidationResponse,
)
from app.models.llm_job_analysis import LLMJobAnalysisOutput
from app.services.profile.evidence import CandidateEvidenceProvider
from app.services.profile.repository import CandidateProfileRepository
from app.infrastructure.openai.job_analysis import JobAnalysisLLM
from app.infrastructure.tracing import ExecutionTraceRecorder
from app.models.tools import ToolDefinition


_SUPPORTED_CLAIM_PREFIXES = (
    r"^hands[-\s]?on experience with\s+",
    r"^practical experience with\s+",
    r"^strong experience with\s+",
    r"^strong experience in\s+",
    r"^experience with\s+",
    r"^experience in\s+",
    r"^experienced with\s+",
    r"^experienced in\s+",
    r"^proficient in\s+",
    r"^knowledge of\s+",
    r"^familiarity with\s+",
    r"^background in\s+",
    r"^strong foundation in\s+",
    r"^strong background in\s+",
    r"^working with\s+",
    r"^worked with\s+",
    r"^skilled in\s+",
)
_SUPPORTED_CLAIM_STOPWORDS = {
    "and",
    "or",
    "with",
    "in",
    "of",
    "to",
    "for",
    "the",
    "a",
    "an",
    "experience",
    "experiences",
    "experienced",
    "practical",
    "strong",
    "hands",
    "hand",
    "on",
    "skilled",
    "skill",
    "skills",
    "proficient",
    "proficiency",
    "knowledge",
    "familiarity",
    "background",
    "building",
    "developing",
    "developed",
    "designing",
    "design",
    "working",
    "worked",
    "maintaining",
    "maintain",
    "using",
    "use",
    "used",
    "creating",
    "create",
    "supporting",
    "support",
    "implementing",
    "implement",
    "managing",
    "manage",
    "handling",
    "handle",
    "development",
}


class ToolCallingJobAnalysisAgent(Protocol):
    def analyze(
        self,
        job_description: str,
        evidence_documents,
        tool_definitions: list[ToolDefinition],
        execute_tool: Callable[[str, dict[str, object]], object],
    ) -> LLMJobAnalysisOutput:
        """Analyze a job and execute only the supplied application tools."""


class JobAnalysisUseCase(Protocol):
    def analyze(self, request: JobAnalysisRequest, run_id: str | None = None) -> JobAnalysisResponse:
        """Validate and analyze one job description."""


class JobAnalysisService:
    def __init__(
        self,
        evidence_provider: CandidateEvidenceProvider,
        llm: JobAnalysisLLM | None,
        repository: CandidateProfileRepository,
        tool_agent: ToolCallingJobAnalysisAgent | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self._evidence_provider = evidence_provider
        self._llm = llm
        self._repository = repository
        self._tool_agent = tool_agent
        self._tool_registry = tool_registry

    def analyze(self, request: JobAnalysisRequest, run_id: str | None = None) -> JobAnalysisResponse:
        trace = ExecutionTraceRecorder("job_analysis", run_id=run_id)
        validation = trace.record(
            "validate_job_description",
            lambda: validate_job_description(request.job_description),
        )
        validation_response = JobValidationResponse(
            is_valid=validation.is_valid,
            normalized_text=validation.normalized_text,
            error_code=validation.error_code,
            message=validation.message,
        )

        if not validation.is_valid:
            return JobAnalysisResponse(
                status="invalid",
                validation=validation_response,
                analysis=None,
                execution_trace=trace.build(status="partial"),
            )

        evidence = trace.record(
            "retrieve_candidate_evidence",
            lambda: self._evidence_provider.get_evidence(validation.normalized_text or ""),
        )
        if self._tool_agent is not None and self._tool_registry is not None:
            llm_output = trace.record(
                "tool_aware_analysis",
                lambda: self._tool_agent.analyze(
                    validation.normalized_text or "",
                    evidence,
                    self._tool_registry.definitions(),
                    self._tool_registry.execute,
                ),
            )
        else:
            if self._llm is None:
                raise RuntimeError("No job-analysis LLM is configured.")
            llm_output = trace.record(
                "llm_analysis",
                lambda: self._llm.analyze(validation.normalized_text or "", evidence),
            )
        analysis = trace.record(
            "ground_candidate_claims",
            lambda: self._build_grounded_analysis(llm_output, evidence),
        )
        return JobAnalysisResponse(
            status="analyzed",
            validation=validation_response,
            analysis=analysis,
            execution_trace=trace.build(status="success"),
        )

    def _build_grounded_analysis(self, output: LLMJobAnalysisOutput, evidence_documents) -> JobAnalysis:
        approved_claims = []
        rejected_claim_count = 0
        for original_claim in output.matched_candidate_claims:
            claim = self._ground_claim_against_retrieved_evidence(original_claim, evidence_documents)
            result = validate_candidate_claim(
                claim,
                self._repository,
            )
            if result.is_allowed:
                approved_claims.append(claim)
            else:
                rejected_claim_count += 1

        grounding_warnings = []
        if rejected_claim_count:
            grounding_warnings.append(
                "Some model-proposed candidate claims lacked sufficient verified evidence and were excluded."
            )

        return JobAnalysis(
            summary=self._build_grounded_summary(approved_claims, output.missing_requirements),
            matched_candidate_claims=approved_claims,
            missing_requirements=output.missing_requirements,
            analysis=self._build_grounded_analysis_text(approved_claims, output.missing_requirements),
            grounding_warnings=grounding_warnings,
        )

    @staticmethod
    def _ground_claim_against_retrieved_evidence(claim: CandidateClaim, evidence_documents) -> CandidateClaim:
        claim_terms = _claim_support_terms(claim.claim)
        if not claim_terms:
            return claim

        for document in evidence_documents:
            if _document_supports_claim(document.content, claim_terms):
                return claim.model_copy(
                    update={
                        "evidence_source": document.source,
                        "evidence_excerpt": document.content,
                    }
                )

        return claim

    @staticmethod
    def _build_grounded_summary(
        approved_claims: list[CandidateClaim],
        missing_requirements: list[str],
    ) -> str:
        claim_text = ", ".join(claim.claim for claim in approved_claims) if approved_claims else "no verified candidate evidence"
        missing_text = ", ".join(missing_requirements) if missing_requirements else "no material gaps identified"
        return f"Verified candidate evidence: {claim_text}. Missing requirements: {missing_text}."

    @staticmethod
    def _build_grounded_analysis_text(
        approved_claims: list[CandidateClaim],
        missing_requirements: list[str],
    ) -> str:
        claim_text = ", ".join(claim.claim for claim in approved_claims) if approved_claims else "No verified candidate claims were approved."
        missing_text = ", ".join(missing_requirements) if missing_requirements else "No missing requirements were identified."
        return (
            f"{claim_text} The analysis is grounded only in approved candidate claims. "
            f"Missing requirements: {missing_text}."
        )


def _claim_support_terms(value: str) -> list[str]:
    cleaned = value.casefold().strip()
    for prefix in _SUPPORTED_CLAIM_PREFIXES:
        cleaned = re.sub(prefix, "", cleaned)
    for separator in ("Â·", "/", "\\", ",", ";", ":", "(", ")", "[", "]", "{", "}", "-", "â€“", "â€”"):
        cleaned = cleaned.replace(separator, " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return [token for token in cleaned.split(" ") if token and token not in _SUPPORTED_CLAIM_STOPWORDS]


def _document_supports_claim(content: str, claim_terms: list[str]) -> bool:
    if not claim_terms:
        return False
    document_terms = set(_claim_support_terms(content))
    return all(term in document_terms for term in claim_terms)
