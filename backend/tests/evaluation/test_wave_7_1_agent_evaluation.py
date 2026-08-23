import json
from pathlib import Path

from app.agent.guardrails import CandidateClaim, validate_candidate_claim
from app.models.job_analysis import JobAnalysisRequest
from app.services.jobs.analysis import JobAnalysisService
from app.services.profile.evidence import DeterministicCandidateEvidenceProvider
from app.services.profile.repository import FileCandidateProfileRepository


REQUIRED_SCENARIOS = [
    "simple-job-no-tool",
    "needs-additional-evidence",
    "specific-project-evidence",
    "multiple-requirements-multiple-tools",
    "unsupported-technology",
    "prompt-injection",
    "insufficient-retrieval",
    "strong-evidence",
    "training-only-evidence",
    "familiarity-not-strong-evidence",
    "best-match-critical-gaps",
    "cover-letter-grounded",
]


def _load_dataset() -> dict:
    dataset_path = Path(__file__).resolve().parents[3] / "data" / "evaluation" / "wave-7.1-agent-evaluation.json"
    return json.loads(dataset_path.read_text(encoding="utf-8"))


def test_wave_7_1_dataset_has_required_scenarios() -> None:
    payload = _load_dataset()
    assert payload["dataset_version"] == "wave-7.1"
    cases = payload["cases"]
    assert len(cases) == 12
    case_ids = [case["id"] for case in cases]
    assert set(REQUIRED_SCENARIOS).issubset(case_ids)
    assert all("canonical_profile_sources" in case for case in cases)
    assert all("job_description" in case for case in cases)
    assert all("expected_behavior" in case for case in cases)

    for case in cases:
        for source in case["canonical_profile_sources"]:
            assert source.startswith("data/profile/")
            assert source.endswith(".md")


def test_wave_7_1_integration_uses_real_repository_and_grounding_guardrails() -> None:
    repository = FileCandidateProfileRepository(Path(__file__).resolve().parents[3] / "data" / "profile")
    evidence_provider = DeterministicCandidateEvidenceProvider(repository)

    class FixtureLLM:
        def analyze(self, job_description: str, evidence_documents: list[object]):
            return type(
                "Output",
                (),
                {
                    "job_summary": "Backend .NET role",
                    "matched_candidate_claims": [
                        CandidateClaim(
                            claim="C#",
                            claim_type="skill",
                            evidence_source="data/profile/skills.md",
                            evidence_excerpt="C# · .NET / ASP.NET Core · Entity Framework Core",
                        ),
                        CandidateClaim(
                            claim="Kubernetes",
                            claim_type="skill",
                            evidence_source="data/profile/skills.md",
                            evidence_excerpt="C# · .NET / ASP.NET Core · Entity Framework Core",
                        ),
                    ],
                    "missing_requirements": ["Kubernetes"],
                    "analysis": "Evaluate the grounded evidence and reject unsupported facts.",
                },
            )()

    response = JobAnalysisService(
        evidence_provider=evidence_provider,
        llm=FixtureLLM(),
        repository=repository,
    ).analyze(JobAnalysisRequest(job_description="We need a backend developer with C# and .NET experience."))

    assert response.status == "analyzed"
    assert response.analysis is not None
    assert response.analysis.matched_candidate_claims
    assert len(response.analysis.matched_candidate_claims) == 1
    assert response.analysis.matched_candidate_claims[0].claim == "C#"
    assert "Some model-proposed candidate claims" in response.analysis.grounding_warnings[0]

    result = validate_candidate_claim(
        CandidateClaim(
            claim="C#",
            claim_type="skill",
            evidence_source="data/profile/skills.md",
            evidence_excerpt="C# · .NET / ASP.NET Core · Entity Framework Core",
        ),
        repository,
    )
    assert result.is_allowed is True
