from collections.abc import Iterable

from app.agent.guardrails import validate_candidate_claim
from app.models.job_analysis import JobAnalysis
from app.models.llm_job_analysis import LLMJobAnalysisOutput
from app.services.profile.repository import CandidateProfileRepository
from app.evaluation.models import EvaluationCase, EvaluationMetrics, EvaluationSummary


def evaluate_case(
    case: EvaluationCase,
    raw_output: LLMJobAnalysisOutput,
    final_analysis: JobAnalysis,
    repository: CandidateProfileRepository,
) -> EvaluationMetrics:
    validation_results = [
        validate_candidate_claim(claim, repository)
        for claim in raw_output.matched_candidate_claims
    ]
    allowed_claims = [
        claim
        for claim, result in zip(raw_output.matched_candidate_claims, validation_results)
        if result.is_allowed
    ]
    rejected_claims = [
        claim
        for claim, result in zip(raw_output.matched_candidate_claims, validation_results)
        if not result.is_allowed
    ]
    raw_count = len(raw_output.matched_candidate_claims)
    rejected_count = len(rejected_claims)
    approved_count = len(allowed_claims)
    final_claim_texts = {claim.claim for claim in final_analysis.matched_candidate_claims}
    allowed_claim_texts = {claim.claim for claim in allowed_claims}
    forbidden_claims_present = [
        forbidden
        for forbidden in case.forbidden_candidate_claims
        if any(
            _normalized(forbidden) in _normalized(claim_text)
            for claim_text in final_claim_texts
        )
    ]
    relevant_claims = [
        claim
        for claim in final_analysis.matched_candidate_claims
        if any(
            _normalized(claim.claim) in _normalized(expected)
            or _normalized(expected) in _normalized(claim.claim)
            for expected in case.expected_relevant_claims
        )
    ]
    expected_missing = [
        requirement
        for requirement in case.expected_missing_requirements
        if any(
            _normalized(requirement) in _normalized(observed)
            or _normalized(observed) in _normalized(requirement)
            for observed in final_analysis.missing_requirements
        )
    ]

    return EvaluationMetrics(
        case_id=case.id,
        grounding=approved_count / raw_count if raw_count else 1.0,
        relevance=(
            len(relevant_claims) / len(final_analysis.matched_candidate_claims)
            if final_analysis.matched_candidate_claims
            else 0.0
        ),
        unsupported_claim_rate=rejected_count / raw_count if raw_count else 0.0,
        missing_evidence_behavior=(
            len(expected_missing) / len(case.expected_missing_requirements)
            if case.expected_missing_requirements
            else 1.0
        ),
        claim_validation_rate=approved_count / raw_count if raw_count else 1.0,
        raw_claim_count=raw_count,
        approved_claim_count=approved_count,
        rejected_claim_count=rejected_count,
        rejected_claims_excluded=final_claim_texts.issubset(allowed_claim_texts),
        forbidden_claims_present=forbidden_claims_present,
        observed_missing_requirements=final_analysis.missing_requirements,
    )


def summarize_metrics(metrics: list[EvaluationMetrics]) -> EvaluationSummary:
    if not metrics:
        return EvaluationSummary(
            case_count=0,
            average_grounding=0.0,
            average_relevance=0.0,
            average_unsupported_claim_rate=0.0,
            average_missing_evidence_behavior=0.0,
            average_claim_validation_rate=0.0,
        )

    return EvaluationSummary(
        case_count=len(metrics),
        average_grounding=_average(metric.grounding for metric in metrics),
        average_relevance=_average(metric.relevance for metric in metrics),
        average_unsupported_claim_rate=_average(
            metric.unsupported_claim_rate for metric in metrics
        ),
        average_missing_evidence_behavior=_average(
            metric.missing_evidence_behavior for metric in metrics
        ),
        average_claim_validation_rate=_average(
            metric.claim_validation_rate for metric in metrics
        ),
    )


def _average(values: Iterable[float]) -> float:
    numeric_values = list(values)
    return sum(numeric_values) / len(numeric_values) if numeric_values else 0.0


def _normalized(value: str) -> str:
    return " ".join(value.split()).casefold()
