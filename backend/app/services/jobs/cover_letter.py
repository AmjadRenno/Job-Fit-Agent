from __future__ import annotations

import re

from app.agent.guardrails import CandidateClaim, validate_candidate_claim
from app.domain.job_validation import validate_job_description
from app.models.cover_letter import CoverLetterClaimDraft, CoverLetterRequest, CoverLetterResponse
from app.models.profile import ProfileDocument
from app.services.jobs.best_match import BestMatchService
from app.services.profile.evidence import CandidateEvidenceProvider
from app.services.profile.repository import CandidateProfileRepository
from app.infrastructure.tracing import ExecutionTraceRecorder


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


class CoverLetterService:
    def __init__(
        self,
        evidence_provider: CandidateEvidenceProvider,
        llm,
        repository: CandidateProfileRepository,
        best_match_service: BestMatchService | None = None,
    ) -> None:
        self._evidence_provider = evidence_provider
        self._llm = llm
        self._repository = repository
        self._best_match_service = best_match_service

    def generate(self, request: CoverLetterRequest, run_id: str | None = None) -> CoverLetterResponse:
        trace = ExecutionTraceRecorder("cover_letter", run_id=run_id) if run_id is not None else None
        validation = (
            trace.record("validate_job_description", lambda: validate_job_description(request.job_description))
            if trace is not None
            else validate_job_description(request.job_description)
        )
        if not validation.is_valid:
            raise ValueError(validation.message)

        evidence_documents = (
            trace.record(
                "retrieve_candidate_evidence",
                lambda: self._evidence_provider.get_evidence(validation.normalized_text or ""),
            )
            if trace is not None
            else self._evidence_provider.get_evidence(validation.normalized_text or "")
        )
        best_match_summary = (
            trace.record(
                "build_match_summary",
                lambda: self._get_relevant_match_summary(request, validation.normalized_text or ""),
            )
            if trace is not None
            else self._get_relevant_match_summary(request, validation.normalized_text or "")
        )
        draft_value = (
            trace.record(
                "generate_candidate_claims",
                lambda: self._llm.generate_claims(
                    request.job_title,
                    request.company_name,
                    validation.normalized_text or "",
                    evidence_documents,
                    best_match_summary,
                    request.language,
                    request.tone,
                ),
            )
            if trace is not None
            else self._llm.generate_claims(
                request.job_title,
                request.company_name,
                validation.normalized_text or "",
                evidence_documents,
                best_match_summary,
                request.language,
                request.tone,
            )
        )
        if isinstance(draft_value, list):
            draft = CoverLetterClaimDraft(candidate_claims=draft_value)
        else:
            draft = draft_value

        approved_claims: list[CandidateClaim] = []
        rejected_claims: list[CandidateClaim] = []
        warnings: list[str] = []

        for original_claim in draft.candidate_claims:
            claim = self._ground_claim_against_retrieved_evidence(original_claim, evidence_documents)
            validation_result = (
                trace.record(
                    "validate_candidate_claims",
                    lambda claim=claim: validate_candidate_claim(claim, self._repository),
                )
                if trace is not None
                else validate_candidate_claim(claim, self._repository)
            )
            if validation_result.is_allowed:
                approved_claims.append(claim)
            else:
                rejected_claims.append(claim)
                warnings.append(f"Rejected candidate claim: {claim.claim} ({validation_result.reason_code})")

        final_letter = (
            trace.record(
                "render_grounded_letter",
                lambda: self._ground_final_letter(request, approved_claims),
            )
            if trace is not None
            else self._ground_final_letter(request, approved_claims)
        )

        if not approved_claims:
            final_letter = self._fallback_cover_letter(request)
            warnings.append("No grounded candidate claims were approved; the letter remains intentionally conservative.")

        if rejected_claims:
            warnings.append("Rejected candidate claims were excluded from the final factual content.")

        return CoverLetterResponse(
            job_id=request.job_id,
            job_title=request.job_title,
            company_name=request.company_name,
            language=request.language,
            cover_letter=final_letter,
            used_candidate_claims=approved_claims,
            grounding_warnings=warnings,
            relevant_match_summary=best_match_summary or "",
            execution_trace=trace.build(status="success") if trace is not None else None,
        )

    @staticmethod
    def _ground_claim_against_retrieved_evidence(
        claim: CandidateClaim,
        evidence_documents: list[ProfileDocument],
    ) -> CandidateClaim:
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

    def _ground_final_letter(
        self,
        request: CoverLetterRequest,
        approved_claims: list[CandidateClaim],
    ) -> str:
        if not approved_claims:
            return self._fallback_cover_letter(request)
        return self._compose_grounded_letter(request, approved_claims)

    def _get_relevant_match_summary(self, request: CoverLetterRequest, job_description: str) -> str:
        if self._best_match_service is None:
            return "Best Match summary not available for this request."

        from app.models.best_match import BestMatchJobInput, BestMatchRequest

        best_match = self._best_match_service.analyze(
            BestMatchRequest(
                jobs=[BestMatchJobInput(id=request.job_id, title=request.job_title, description=job_description)]
            )
        )
        if best_match.best_match is None:
            return "No best-match summary available."

        strengths = ", ".join(best_match.best_match.matched_requirements[:5]) or "relevant candidate strengths"
        gaps = ", ".join(best_match.best_match.missing_requirements[:5]) or "no major gaps identified"
        return f"Top strengths: {strengths}. Key gaps: {gaps}."

    @staticmethod
    def _fallback_cover_letter(request: CoverLetterRequest) -> str:
        company_block = request.company_name or "your company"
        if request.language == "da":
            return (
                f"Kære rekrutteringsansvarlig,\n\nJeg er meget interesseret i stillingen som {request.job_title} hos {company_block}. "
                f"Jeg vil være glad for at diskutere, hvordan min baggrund kan støtte jeres mål og behov.\n\nMed venlig hilsen,\n[Candidate]"
            )
        return (
            f"Dear Hiring Manager,\n\nI am very interested in the {request.job_title} opportunity at {company_block}. "
            f"I would welcome the opportunity to discuss how my background can support the team and contribute to your goals.\n\nKind regards,\n[Candidate]"
        )

    @staticmethod
    def _compose_grounded_letter(
        request: CoverLetterRequest,
        approved_claims: list[CandidateClaim],
    ) -> str:
        company_block = request.company_name or "your company"
        claim_text = ", ".join(claim.claim for claim in approved_claims[:4])
        if request.language == "da":
            return (
                f"Kære rekrutteringsansvarlig,\n\n"
                f"Jeg er meget interesseret i stillingen som {request.job_title} hos {company_block}. "
                f"Min dokumenterede baggrund omfatter {claim_text}. "
                f"Jeg vil gerne drøfte, hvordan denne dokumenterede erfaring kan støtte jeres team.\n\n"
                f"Med venlig hilsen,\n[Candidate]"
            )
        return (
            f"Dear Hiring Manager,\n\n"
            f"I am interested in the {request.job_title} opportunity at {company_block}. "
            f"My documented background includes {claim_text}. "
            f"I would welcome the opportunity to discuss how this grounded experience can support your team.\n\n"
            f"Kind regards,\n[Candidate]"
        )


def _claim_support_terms(value: str) -> list[str]:
    cleaned = value.casefold().strip()
    for prefix in _SUPPORTED_CLAIM_PREFIXES:
        cleaned = re.sub(prefix, "", cleaned)
    for separator in ("·", "/", "\\", ",", ";", ":", "(", ")", "[", "]", "{", "}", "-", "–", "—"):
        cleaned = cleaned.replace(separator, " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return [token for token in cleaned.split(" ") if token and token not in _SUPPORTED_CLAIM_STOPWORDS]


def _document_supports_claim(content: str, claim_terms: list[str]) -> bool:
    if not claim_terms:
        return False
    document_terms = set(_claim_support_terms(content))
    return all(term in document_terms for term in claim_terms)
