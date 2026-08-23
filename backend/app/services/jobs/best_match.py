from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from app.agent.guardrails import (
    CandidateClaim,
    _claim_terms_supported,
    _normalize_claim_terms,
    validate_candidate_claim,
)
from app.models.best_match import (
    BestMatchJobInput,
    BestMatchRequest,
    BestMatchResponse,
    JobMatchResult,
    JobRequirement,
)
from app.models.job_analysis import JobAnalysisRequest
from app.models.profile import ProfileDocument
from app.services.profile.evidence import CandidateEvidenceProvider
from app.services.profile.repository import CandidateProfileRepository
from app.services.jobs.analysis import JobAnalysisService
from app.infrastructure.tracing import ExecutionTraceRecorder


class JobMatchingLLM(Protocol):
    def extract_requirements(
        self,
        job_description: str,
        evidence_documents: list[ProfileDocument],
    ) -> list[JobRequirement]:
        """Return normalized requirements extracted from the supplied job description."""


@dataclass(frozen=True)
class MatchWeights:
    required_match: float = 1.0
    required_partial: float = 0.5
    required_missing: float = 0.0
    required_unknown: float = 0.0
    preferred_match: float = 0.5
    preferred_partial: float = 0.25
    preferred_missing: float = 0.0
    preferred_unknown: float = 0.0


class BestMatchService:
    _weights = MatchWeights()
    _critical_keywords = (
        "must have",
        "required",
        "mandatory",
        "essential",
        "experience",
        "degree",
        "certification",
    )

    def __init__(
        self,
        evidence_provider: CandidateEvidenceProvider | None,
        llm: JobMatchingLLM | None,
        repository: CandidateProfileRepository | None,
        analysis_service: JobAnalysisService | None = None,
    ) -> None:
        self._evidence_provider = evidence_provider
        self._llm = llm
        self._repository = repository
        self._analysis_service = analysis_service

    def analyze(self, request: BestMatchRequest, run_id: str | None = None) -> BestMatchResponse:
        if not request.jobs:
            raise ValueError("At least one job is required for best-match analysis.")

        trace = ExecutionTraceRecorder("best_match", run_id=run_id) if run_id is not None else None
        analyzed_jobs = []
        for job in request.jobs:
            if trace is not None:
                analyzed_jobs.append(
                    trace.record(f"analyze_job:{job.id}", lambda job=job: self._analyze_job(job))
                )
            else:
                analyzed_jobs.append(self._analyze_job(job))

        if trace is not None:
            ranked = trace.record("rank_jobs", lambda: self._rank_jobs(analyzed_jobs))
        else:
            ranked = self._rank_jobs(analyzed_jobs)
        best_match = ranked[0] if ranked else None
        if best_match is None:
            return BestMatchResponse(ranked_jobs=[], best_match=None, execution_trace=trace.build(status="partial") if trace is not None else None)

        explanation = best_match.match_summary
        strengths = [
            requirement.requirement
            for requirement in best_match.requirement_results
            if requirement.status == "matched"
        ][:5]
        gaps = [
            requirement.requirement
            for requirement in best_match.requirement_results
            if requirement.status in {"missing", "partially_matched"}
        ][:5]

        response = BestMatchResponse(
            ranked_jobs=ranked,
            best_match=best_match,
            score=best_match.score,
            concise_explanation=explanation,
            important_strengths=strengths,
            important_gaps=gaps,
            execution_trace=trace.build(status="success") if trace is not None else None,
        )
        return response

    def _analyze_job(self, job: BestMatchJobInput) -> JobMatchResult:
        evidence_documents: list[ProfileDocument] = []
        approved_claims: list[CandidateClaim] = []
        if self._analysis_service is not None:
            analysis_response = self._analysis_service.analyze(
                JobAnalysisRequest(job_description=job.description)
            )
            if analysis_response.analysis is not None:
                approved_claims = analysis_response.analysis.matched_candidate_claims
        if self._evidence_provider is not None:
            evidence_documents = self._evidence_provider.get_evidence(job.description)

        requirements = self._extract_requirements(job.description)
        if self._llm is not None and hasattr(self._llm, "extract_requirements"):
            try:
                llm_requirements = self._llm.extract_requirements(job.description, evidence_documents)
                if llm_requirements:
                    requirements = llm_requirements
            except Exception:
                requirements = self._extract_requirements(job.description)

        evaluated = [
            self._evaluate_requirement(requirement, evidence_documents, approved_claims)
            for requirement in requirements
        ]
        return self._build_job_result(job, evaluated)

    def _extract_requirements(self, job_description: str) -> list[JobRequirement]:
        text = " ".join(job_description.split())
        if not text:
            return []

        requirement_phrases = self._split_requirements(text)
        requirements: list[JobRequirement] = []
        for phrase in requirement_phrases:
            normalized = self._normalize_requirement(phrase)
            if not normalized:
                continue
            importance = self._classify_importance(normalized)
            requirement_type = self._classify_requirement_type(normalized)
            requirements.append(
                JobRequirement(
                    requirement=normalized,
                    requirement_type=requirement_type,
                    importance=importance,
                    matched_candidate_claims=[],
                    status="unknown",
                    evidence=[],
                )
            )
        if not requirements:
            return [
                JobRequirement(
                    requirement=text[:120],
                    requirement_type="other",
                    importance="unknown",
                    matched_candidate_claims=[],
                    status="unknown",
                    evidence=[],
                )
            ]
        return requirements

    def _split_requirements(self, text: str) -> list[str]:
        sentence_chunks = re.split(r"\.(?=\s|$)|[;\n]", text)
        candidates: list[str] = []
        for chunk in sentence_chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            parts = [part.strip() for part in re.split(r",| and | or |/", chunk) if part.strip()]
            candidates.extend(part for part in parts if len(part) > 2)
        deduped: list[str] = []
        for item in candidates:
            if item.lower() not in {entry.lower() for entry in deduped}:
                deduped.append(item)
        return deduped

    def _classify_importance(self, requirement: str) -> str:
        lowered = requirement.lower()
        if any(
            token in lowered
            for token in (
                "preferred",
                "nice to have",
                "nice-to-have",
                "desirable",
                "bonus",
                "plus",
            )
        ):
            return "preferred"
        if any(
            token in lowered
            for token in (
                "must have",
                "must",
                "required",
                "mandatory",
                "essential",
            )
        ):
            return "required"
        if "experience" in lowered:
            return "required"
        return "unknown"

    def _classify_requirement_type(self, requirement: str) -> str:
        lowered = requirement.lower()
        if any(token in lowered for token in ("degree", "bachelor", "master", "education")):
            return "education"
        if "experience" in lowered:
            return "experience"
        if any(token in lowered for token in ("certification", "certified")):
            return "certification"
        if any(token in lowered for token in ("api", "rest", "sql", "docker", "kubernetes", "react", "typescript", "javascript", "python", "c#", ".net", "asp.net", "rag", "llm", "agent", "openai", "mcp", "langgraph", "azure", "terraform")):
            return "technology"
        if any(token in lowered for token in ("build", "maintain", "develop", "design", "support", "deliver")):
            return "responsibility"
        return "other"

    def _normalize_requirement(self, requirement: str) -> str:
        normalized = re.sub(r"\s+", " ", requirement).strip(" -:;,. ")
        return normalized.strip()

    def _evaluate_requirement(
        self,
        requirement: JobRequirement,
        evidence_documents: list[ProfileDocument] | None = None,
        approved_claims: list[CandidateClaim] | None = None,
    ) -> JobRequirement:
        evidence_documents = evidence_documents or []

        if not requirement.matched_candidate_claims:
            if approved_claims is not None:
                requirement.matched_candidate_claims = [
                    claim
                    for claim in approved_claims
                    if self._claim_supports_requirement(claim, requirement.requirement)
                ]
                requirement.evidence = list({claim.evidence_excerpt for claim in requirement.matched_candidate_claims})
            else:
                requirement.status = "missing"
                return requirement

        if self._repository is not None:
            approved_claims: list[CandidateClaim] = []
            for claim in requirement.matched_candidate_claims:
                result = validate_candidate_claim(claim, self._repository)
                if result.is_allowed:
                    approved_claims.append(claim)
            requirement.matched_candidate_claims = approved_claims
            requirement.evidence = list({claim.evidence_excerpt for claim in approved_claims})

        if not requirement.matched_candidate_claims:
            requirement.status = "missing"
            return requirement

        requirement_parts = [
            part
            for part in self._extract_requirement_claim_candidates(requirement.requirement)
            if _normalize_claim_terms(part)
        ]
        supported_parts = [
            part
            for part in requirement_parts
            if any(_claim_terms_supported(claim.claim, part) for claim in requirement.matched_candidate_claims)
        ]
        if supported_parts and len(supported_parts) == len(requirement_parts):
            requirement.status = "matched"
            return requirement

        requirement.status = "partially_matched"
        return requirement

    def _claim_supports_requirement(self, claim: CandidateClaim, requirement: str) -> bool:
        requirement_parts = [
            part
            for part in self._extract_requirement_claim_candidates(requirement)
            if _normalize_claim_terms(part)
        ]
        return any(_claim_terms_supported(claim.claim, part) for part in requirement_parts)

    def _extract_requirement_claim_candidates(self, requirement: str) -> list[str]:
        pieces = [piece.strip() for piece in re.split(r"\band\b|\bwith\b|\bor\b|,|/|;", requirement.lower()) if piece.strip()]
        claims: list[str] = []
        for piece in pieces:
            cleaned = self._normalize_requirement(piece)
            if cleaned and len(cleaned) > 1:
                claims.append(cleaned)
        if not claims:
            claims = [self._normalize_requirement(requirement)]
        return claims

    @staticmethod
    def _candidate_claim_type(requirement_type: str) -> str:
        if requirement_type in {"required_skill", "preferred_skill", "technology"}:
            return "skill"
        if requirement_type in {"experience", "education", "certification"}:
            return requirement_type
        return "other"

    def _build_job_result(self, job: BestMatchJobInput, requirements: list[JobRequirement]) -> JobMatchResult:
        weighted_requirements = [self._calculate_requirement_score(req) for req in requirements]
        total = sum(weighted_requirements)
        max_score = max(sum(
            self._max_requirement_weight(req.importance, "matched") for req in requirements
        ), 1.0)
        normalized_score = (total / max_score) * 100 if max_score else 0.0
        raw = round(normalized_score, 2)

        matched = [req.requirement for req in requirements if req.status == "matched"]
        partial = [req.requirement for req in requirements if req.status == "partially_matched"]
        missing = [req.requirement for req in requirements if req.status == "missing"]
        critical = [req.requirement for req in requirements if self._is_critical_gap(req)]
        evidence = [
            excerpt
            for req in requirements
            for excerpt in req.evidence
        ]
        summary = self._build_summary(job.title or job.id, matched, partial, missing, critical)

        return JobMatchResult(
            job_id=job.id,
            title=job.title,
            score=raw,
            match_summary=summary,
            requirement_results=requirements,
            matched_requirements=matched,
            partial_matches=partial,
            missing_requirements=missing,
            critical_gaps=critical,
            supporting_candidate_evidence=evidence,
        )

    @staticmethod
    def _calculate_requirement_score(requirement: JobRequirement) -> float:
        weights = MatchWeights()
        if requirement.importance == "preferred":
            mapping = {
                "matched": weights.preferred_match,
                "partially_matched": weights.preferred_partial,
                "missing": weights.preferred_missing,
                "unknown": weights.preferred_unknown,
            }
        elif requirement.importance == "required":
            mapping = {
                "matched": weights.required_match,
                "partially_matched": weights.required_partial,
                "missing": weights.required_missing,
                "unknown": weights.required_unknown,
            }
        else:
            mapping = {
                "matched": 0.5,
                "partially_matched": 0.25,
                "missing": 0.0,
                "unknown": 0.0,
            }
        return float(mapping.get(requirement.status, 0.0))

    def _max_requirement_weight(self, importance: str, status: str) -> float:
        if importance == "preferred":
            return self._weights.preferred_match
        if importance == "required":
            return self._weights.required_match
        return 0.5

    @staticmethod
    def _is_critical_gap(requirement: JobRequirement) -> bool:
        if requirement.importance != "required":
            return False
        if requirement.status != "missing":
            return False
        if requirement.requirement_type in {"required_skill", "technology", "experience", "education"}:
            return True
        lower = requirement.requirement.lower()
        return any(keyword in lower for keyword in BestMatchService._critical_keywords)

    def _rank_jobs(self, jobs: list[JobMatchResult]) -> list[JobMatchResult]:
        ranked = sorted(
            jobs,
            key=lambda item: (
                -item.score,
                -sum(self._calculate_requirement_score(req) for req in item.requirement_results if req.importance == "required"),
                len(item.critical_gaps),
                item.job_id,
            ),
        )
        for index, item in enumerate(ranked, start=1):
            item.rank = index
        return ranked

    def _build_summary(
        self,
        title: str,
        matched: list[str],
        partial: list[str],
        missing: list[str],
        critical: list[str],
    ) -> str:
        strengths = ", ".join(matched[:3]) if matched else "No strong verified requirements matched"
        gaps = ", ".join(missing[:3]) if missing else "No major gaps identified"
        critical_note = " Critical required gaps remain." if critical else ""
        return f"{title}: strongest evidence includes {strengths}; gaps include {gaps}.{critical_note}"
