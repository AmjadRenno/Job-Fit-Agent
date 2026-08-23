from pathlib import Path

import pytest

from app.agent.guardrails import CandidateClaim, validate_candidate_claim
from app.services.profile.repository import FileCandidateProfileRepository


@pytest.fixture
def repository() -> FileCandidateProfileRepository:
    repository_root = Path(__file__).resolve().parents[3]
    return FileCandidateProfileRepository(repository_root / "data" / "profile")


def test_supported_skill_claim_is_allowed(repository: FileCandidateProfileRepository) -> None:
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
    assert result.reason_code == "supported_claim"


def test_unsupported_skill_claim_is_rejected(repository: FileCandidateProfileRepository) -> None:
    result = validate_candidate_claim(
        CandidateClaim(
            claim="Rust",
            claim_type="skill",
            evidence_source="data/profile/skills.md",
            evidence_excerpt="C# · .NET / ASP.NET Core · Entity Framework Core",
        ),
        repository,
    )

    assert result.is_allowed is False
    assert result.reason_code == "claim_not_supported"


def test_unsupported_experience_claim_is_rejected(repository: FileCandidateProfileRepository) -> None:
    result = validate_candidate_claim(
        CandidateClaim(
            claim="Managed a team of ten engineers",
            claim_type="experience",
            evidence_source="data/profile/experience.md",
            evidence_excerpt="Backend development and frontend development",
        ),
        repository,
    )

    assert result.is_allowed is False
    assert result.reason_code == "claim_not_supported"


def test_unsupported_project_claim_is_rejected(repository: FileCandidateProfileRepository) -> None:
    result = validate_candidate_claim(
        CandidateClaim(
            claim="Production banking platform",
            claim_type="project",
            evidence_source="data/profile/projects/portfolio.md",
            evidence_excerpt="Personal portfolio built with Next.js 16, TypeScript, and Tailwind CSS",
        ),
        repository,
    )

    assert result.is_allowed is False
    assert result.reason_code == "claim_not_supported"


def test_unsupported_education_claim_is_rejected(repository: FileCandidateProfileRepository) -> None:
    result = validate_candidate_claim(
        CandidateClaim(
            claim="Master's degree in Computer Science",
            claim_type="education",
            evidence_source="data/profile/education.md",
            evidence_excerpt="Datamatiker (Computer Science AP) — UCL, Vejle",
        ),
        repository,
    )

    assert result.is_allowed is False
    assert result.reason_code == "claim_not_supported"


def test_course_only_evidence_cannot_support_professional_experience(repository: FileCandidateProfileRepository) -> None:
    result = validate_candidate_claim(
        CandidateClaim(
            claim="Building Agentic AI Systems for Developers",
            claim_type="experience",
            evidence_source="data/profile/certifications.md",
            evidence_excerpt="Building Agentic AI Systems for Developers (Learning Path, 11 courses, 15h 33m)",
        ),
        repository,
    )

    assert result.is_allowed is False
    assert result.reason_code == "course_not_professional_experience"


def test_unknown_evidence_is_rejected_safely(repository: FileCandidateProfileRepository) -> None:
    result = validate_candidate_claim(
        CandidateClaim(
            claim="C#",
            claim_type="skill",
            evidence_source="data/profile/unknown.md",
            evidence_excerpt="C#",
        ),
        repository,
    )

    assert result.is_allowed is False
    assert result.reason_code == "unknown_evidence_source"


def test_familiarity_evidence_cannot_support_advanced_claim(repository: FileCandidateProfileRepository) -> None:
    result = validate_candidate_claim(
        CandidateClaim(
            claim="Advanced Apache Kafka",
            claim_type="skill",
            evidence_source="data/profile/skills.md",
            evidence_excerpt="Apache Kafka · RabbitMQ · Redis",
        ),
        repository,
    )

    assert result.is_allowed is False
    assert result.reason_code == "evidence_level_overstated"


def test_mixed_skills_document_does_not_treat_tier_one_as_familiarity(
    repository: FileCandidateProfileRepository,
) -> None:
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


def test_generic_wrappers_can_still_ground_supported_claims(repository: FileCandidateProfileRepository) -> None:
    result = validate_candidate_claim(
        CandidateClaim(
            claim="Experience with C# and ASP.NET Core",
            claim_type="skill",
            evidence_source="data/profile/skills.md",
            evidence_excerpt="C# · .NET / ASP.NET Core · Entity Framework Core · SQL / relational databases · REST APIs",
        ),
        repository,
    )

    assert result.is_allowed is True
    assert result.reason_code == "supported_claim"


@pytest.mark.parametrize(
    ("project_id", "evidence_excerpt"),
    [
        ("edc", ".NET 8, Windows Forms, Clean Architecture with MVP pattern"),
        ("scooterland", "Blazor WebAssembly + Radzen Components (frontend)"),
    ],
)
def test_academic_training_projects_cannot_support_professional_experience(
    repository: FileCandidateProfileRepository,
    project_id: str,
    evidence_excerpt: str,
) -> None:
    claim = "Clean Architecture" if project_id == "edc" else "Blazor WebAssembly"
    result = validate_candidate_claim(
        CandidateClaim(
            claim=claim,
            claim_type="experience",
            evidence_source=f"data/profile/projects/{project_id}.md",
            evidence_excerpt=evidence_excerpt,
        ),
        repository,
    )

    assert result.is_allowed is False
    assert result.reason_code == "course_not_professional_experience"


def test_natural_language_claim_is_rejected_by_literal_matching(
    repository: FileCandidateProfileRepository,
) -> None:
    result = validate_candidate_claim(
        CandidateClaim(
            claim="The candidate has strong hands-on experience with C# and .NET",
            claim_type="skill",
            evidence_source="data/profile/skills.md",
            evidence_excerpt=(
                "C# · .NET / ASP.NET Core · Entity Framework Core · SQL / relational databases · "
                "REST APIs · Clean Architecture · Web application development · Backend development · "
                "Full-stack development · Docker · Testing (xUnit, NUnit, Moq) · Git / GitHub · "
                "React / TypeScript · Blazor · JavaScript · Security-aware application development · "
                "UML / architecture documentation · Authentication / authorization"
            ),
        ),
        repository,
    )

    assert result.is_allowed is False
    assert result.reason_code == "claim_not_supported"
