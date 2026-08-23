from pathlib import Path

import pytest

from app.agent.guardrails import CandidateClaim
from app.models.cover_letter import CoverLetterRequest
from app.services.jobs.cover_letter import CoverLetterService
from app.services.profile.repository import FileCandidateProfileRepository


@pytest.fixture
def repository() -> FileCandidateProfileRepository:
    repo_root = Path(__file__).resolve().parents[3]
    return FileCandidateProfileRepository(repo_root / "data" / "profile")


class FakeEvidenceProvider:
    def __init__(self, documents):
        self._documents = documents

    def get_evidence(self, query: str):
        del query
        return self._documents


class FakeLLM:
    def generate_claims(
        self,
        job_title: str,
        company_name: str | None,
        job_description: str,
        evidence_documents,
        best_match_summary: str,
        language: str,
        tone: str,
    ):
        del job_title, company_name, job_description, best_match_summary, language, tone
        return [
            CandidateClaim(
                claim="C#",
                claim_type="skill",
                evidence_source="data/profile/skills.md",
                evidence_excerpt="C#",
            ),
            CandidateClaim(
                claim="Rust",
                claim_type="skill",
                evidence_source="data/profile/skills.md",
                evidence_excerpt="Rust",
            ),
        ]


class ClaimOnlyLLM:
    def generate_claims(
        self,
        job_title: str,
        company_name: str | None,
        job_description: str,
        evidence_documents,
        best_match_summary: str,
        language: str,
        tone: str,
    ):
        del job_title, company_name, job_description, evidence_documents, best_match_summary, language, tone
        return [
            CandidateClaim(
                claim="C#",
                claim_type="skill",
                evidence_source="data/profile/skills.md",
                evidence_excerpt="C#",
            )
        ]


class GroundablePrefixLLM:
    def generate_claims(
        self,
        job_title: str,
        company_name: str | None,
        job_description: str,
        evidence_documents,
        best_match_summary: str,
        language: str,
        tone: str,
    ):
        del job_title, company_name, job_description, evidence_documents, best_match_summary, language, tone
        return [
            CandidateClaim(
                claim="Experience with C# and ASP.NET Core",
                claim_type="skill",
                evidence_source="data/profile/unknown.md",
                evidence_excerpt="Experience with C# and ASP.NET Core",
            ),
            CandidateClaim(
                claim="Knowledge of Docker",
                claim_type="skill",
                evidence_source="profile/projects/portfolio.md",
                evidence_excerpt="Knowledge of Docker",
            ),
        ]


def test_cover_letter_valid_request_and_language_validation() -> None:
    request = CoverLetterRequest(
        job_id="job-1",
        job_title="Senior .NET Developer",
        company_name="Contoso",
        job_description="We are hiring a .NET developer with C# and ASP.NET Core experience.",
        language="en",
        tone="professional",
    )
    assert request.job_title == "Senior .NET Developer"
    assert request.language == "en"

    with pytest.raises(ValueError):
        CoverLetterRequest(
            job_id="job-2",
            job_title="Developer",
            company_name="Contoso",
            job_description="We are hiring a .NET developer with C# and ASP.NET Core experience.",
            language="fr",
        )

    with pytest.raises(ValueError):
        CoverLetterRequest(
            job_id="job-3",
            job_title="Developer",
            company_name="Contoso",
            job_description="We are hiring a .NET developer with C# and ASP.NET Core experience.",
            tone="verbose",
        )


def test_cover_letter_service_filters_unsupported_claims(repository: FileCandidateProfileRepository) -> None:
    service = CoverLetterService(
        evidence_provider=FakeEvidenceProvider([repository.get_skills()]),
        llm=FakeLLM(),
        repository=repository,
        best_match_service=None,
    )

    response = service.generate(
        CoverLetterRequest(
            job_id="job-1",
            job_title="Senior .NET Developer",
            company_name="Contoso",
            job_description="We are hiring a .NET developer with C# and ASP.NET Core experience.",
            language="en",
            tone="professional",
        )
    )

    assert response.cover_letter
    assert any(claim.claim == "C#" for claim in response.used_candidate_claims)
    assert all(claim.claim != "Rust" for claim in response.used_candidate_claims)
    assert any("Rust" in warning for warning in response.grounding_warnings)
    assert "Rust" not in response.cover_letter
    assert "C#" in response.cover_letter


def test_cover_letter_service_does_not_require_compose_step(repository: FileCandidateProfileRepository) -> None:
    service = CoverLetterService(
        evidence_provider=FakeEvidenceProvider([repository.get_skills()]),
        llm=ClaimOnlyLLM(),
        repository=repository,
        best_match_service=None,
    )

    response = service.generate(
        CoverLetterRequest(
            job_id="job-2",
            job_title="Senior .NET Developer",
            company_name="Contoso",
            job_description="We are hiring a .NET developer with C# and ASP.NET Core experience.",
            language="en",
            tone="professional",
        )
    )

    assert response.cover_letter
    assert "C#" in response.cover_letter
    assert "Rust" not in response.cover_letter


def test_cover_letter_service_accepts_supported_generic_wrappers(repository: FileCandidateProfileRepository) -> None:
    service = CoverLetterService(
        evidence_provider=FakeEvidenceProvider([repository.get_skills()]),
        llm=GroundablePrefixLLM(),
        repository=repository,
        best_match_service=None,
    )

    response = service.generate(
        CoverLetterRequest(
            job_id="job-3",
            job_title="Senior .NET Developer",
            company_name="Contoso",
            job_description="We are hiring a .NET developer with C# and ASP.NET Core experience.",
            language="en",
            tone="professional",
        )
    )

    assert response.used_candidate_claims
    assert any(claim.claim == "Experience with C# and ASP.NET Core" for claim in response.used_candidate_claims)
    assert any(claim.claim == "Knowledge of Docker" for claim in response.used_candidate_claims)
    assert all(claim.evidence_source == "data/profile/skills.md" for claim in response.used_candidate_claims)
    assert not response.grounding_warnings
    assert "C# and ASP.NET Core" in response.cover_letter
    assert "Docker" in response.cover_letter


def test_cover_letter_dataset_contains_expected_job_profiles() -> None:
    dataset_path = Path(__file__).resolve().parents[3] / "data" / "evaluation" / "cover_letter_jobs.json"
    assert dataset_path.exists()
    payload = dataset_path.read_text(encoding="utf-8")
    assert ".NET" in payload
    assert "AI" in payload
    assert "backend" in payload
