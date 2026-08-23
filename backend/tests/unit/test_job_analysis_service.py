from pathlib import Path

from app.models.job_analysis import JobAnalysis, JobAnalysisRequest
from app.models.llm_job_analysis import LLMJobAnalysisOutput
from app.services.jobs.analysis import JobAnalysisService
from app.services.profile.evidence import DeterministicCandidateEvidenceProvider
from app.services.profile.repository import FileCandidateProfileRepository


def build_service(llm: object) -> JobAnalysisService:
    repository = FileCandidateProfileRepository(
        Path(__file__).resolve().parents[3] / "data" / "profile"
    )
    return JobAnalysisService(
        evidence_provider=DeterministicCandidateEvidenceProvider(repository),
        llm=llm,
        repository=repository,
    )


def test_llm_service_returns_grounded_analysis() -> None:
    class FakeLLM:
        def analyze(self, job_description: str, evidence: list[object]) -> LLMJobAnalysisOutput:
            return LLMJobAnalysisOutput(
                job_summary="Backend role with Rust leadership responsibilities",
                matched_candidate_claims=[
                    {
                        "claim": "C#",
                        "claim_type": "skill",
                        "evidence_source": "data/profile/skills.md",
                        "evidence_excerpt": "C# · .NET / ASP.NET Core · Entity Framework Core",
                    },
                    {
                        "claim": "Rust",
                        "claim_type": "skill",
                        "evidence_source": "data/profile/skills.md",
                        "evidence_excerpt": "C# · .NET / ASP.NET Core · Entity Framework Core",
                    },
                ],
                missing_requirements=["Kubernetes"],
                analysis="The candidate has verified backend evidence and managed a team of ten engineers.",
            )

    service = build_service(FakeLLM())
    request = JobAnalysisRequest(
        job_description="We are hiring a Python engineer to build reliable APIs."
    )

    response = service.analyze(request)

    assert response.status == "analyzed"
    assert response.validation.is_valid is True
    assert response.validation.normalized_text == request.job_description
    assert response.analysis is not None
    assert [claim.claim for claim in response.analysis.matched_candidate_claims] == ["C#"]
    assert "Rust" not in response.analysis.model_dump_json()
    assert "managed a team of ten engineers" not in response.analysis.model_dump_json()
    assert "C#" in response.analysis.summary
    assert "Kubernetes" in response.analysis.analysis
    assert response.analysis.grounding_warnings == [
        "Some model-proposed candidate claims lacked sufficient verified evidence and were excluded."
    ]
    assert response.analysis.missing_requirements == ["Kubernetes"]


def test_invalid_job_does_not_call_llm() -> None:
    class FailingLLM:
        def analyze(self, job_description: str, evidence: list[object]) -> LLMJobAnalysisOutput:
            raise AssertionError("LLM must not be called for invalid jobs")

    response = build_service(FailingLLM()).analyze(JobAnalysisRequest(job_description=" "))

    assert response.status == "invalid"
    assert response.analysis is None


def test_job_analysis_has_explicit_context_fields() -> None:
    analysis = JobAnalysis(
        experience_level="senior",
        education=["Bachelor's degree in Computer Science"],
        location="Remote",
    )

    assert analysis.experience_level == "senior"
    assert analysis.education == ["Bachelor's degree in Computer Science"]
    assert analysis.location == "Remote"


def test_invalid_request_returns_structured_validation_response() -> None:
    response = build_service(object()).analyze(JobAnalysisRequest(job_description=" "))

    assert response.status == "invalid"
    assert response.validation.model_dump() == {
        "is_valid": False,
        "normalized_text": None,
        "error_code": "empty_job_description",
        "message": "A job description is required.",
    }
    assert response.analysis is None
