from __future__ import annotations

from pathlib import Path

import pytest

from app.agent.guardrails import CandidateClaim
from app.models.best_match import (
    BestMatchJobInput,
    BestMatchRequest,
    BestMatchResponse,
    JobRequirement,
)
from app.services.jobs.best_match import BestMatchService
from app.services.profile.repository import FileCandidateProfileRepository


@pytest.fixture
def repository() -> FileCandidateProfileRepository:
    repo_root = Path(__file__).resolve().parents[3]
    return FileCandidateProfileRepository(repo_root / "data" / "profile")


def test_requirement_classification_and_matches() -> None:
    required = JobRequirement(
        requirement="C# and ASP.NET Core",
        requirement_type="required_skill",
        importance="required",
        matched_candidate_claims=[
            CandidateClaim(
                claim="C#",
                claim_type="skill",
                evidence_source="data/profile/skills.md",
                evidence_excerpt="C# · .NET / ASP.NET Core · Entity Framework Core",
            )
        ],
        status="matched",
        evidence=["C# · .NET / ASP.NET Core · Entity Framework Core"],
    )
    preferred = JobRequirement(
        requirement="Kubernetes",
        requirement_type="technology",
        importance="preferred",
        matched_candidate_claims=[],
        status="missing",
        evidence=[],
    )

    assert required.importance == "required"
    assert preferred.importance == "preferred"
    assert required.status == "matched"
    assert preferred.status == "missing"


def test_scoring_and_critical_gap_are_deterministic() -> None:
    requirement_a = JobRequirement(
        requirement="C#",
        requirement_type="required_skill",
        importance="required",
        matched_candidate_claims=[
            CandidateClaim(
                claim="C#",
                claim_type="skill",
                evidence_source="data/profile/skills.md",
                evidence_excerpt="C# · .NET / ASP.NET Core · Entity Framework Core",
            )
        ],
        status="matched",
        evidence=["C# · .NET / ASP.NET Core · Entity Framework Core"],
    )
    requirement_b = JobRequirement(
        requirement="Kubernetes",
        requirement_type="technology",
        importance="required",
        matched_candidate_claims=[],
        status="missing",
        evidence=[],
    )

    score = BestMatchService._calculate_requirement_score(requirement_a)
    assert score == 1.0
    assert BestMatchService._calculate_requirement_score(requirement_b) == 0.0
    assert BestMatchService._is_critical_gap(requirement_b) is True


def test_experience_markers_preserve_preferred_vs_required_importance_and_scoring() -> None:
    service = BestMatchService(
        evidence_provider=None,  # type: ignore[arg-type]
        llm=None,  # type: ignore[arg-type]
        repository=None,  # type: ignore[arg-type]
    )

    required = service._extract_requirements("required experience with C#")[0]
    preferred = service._extract_requirements("preferred experience with Docker")[0]
    mandatory = service._extract_requirements("mandatory experience with Kubernetes")[0]
    nice_to_have = service._extract_requirements("nice-to-have experience with testing")[0]

    assert required.importance == "required"
    assert preferred.importance == "preferred"
    assert mandatory.importance == "required"
    assert nice_to_have.importance == "preferred"

    required.status = "matched"
    required.matched_candidate_claims = [
        CandidateClaim(
            claim="C#",
            claim_type="skill",
            evidence_source="data/profile/skills.md",
            evidence_excerpt="C# · .NET / ASP.NET Core · Entity Framework Core",
        )
    ]
    required.evidence = ["C# · .NET / ASP.NET Core · Entity Framework Core"]

    preferred.status = "matched"
    preferred.matched_candidate_claims = [
        CandidateClaim(
            claim="Docker",
            claim_type="skill",
            evidence_source="data/profile/skills.md",
            evidence_excerpt="Docker · Testing (xUnit, NUnit, Moq)",
        )
    ]
    preferred.evidence = ["Docker · Testing (xUnit, NUnit, Moq)"]

    mandatory.status = "missing"
    nice_to_have.status = "missing"

    result = service._build_job_result(
        job=BestMatchJobInput(id="job-importance", title="Importance Check", description="placeholder"),
        requirements=[required, preferred, mandatory, nice_to_have],
    )

    assert result.score == 50.0
    assert result.critical_gaps == ["mandatory experience with Kubernetes"]


def test_unsupported_claim_is_rejected_and_cannot_affect_score(repository: FileCandidateProfileRepository) -> None:
    service = BestMatchService(
        evidence_provider=None,  # type: ignore[arg-type]
        llm=None,  # type: ignore[arg-type]
        repository=repository,
    )

    requirement = JobRequirement(
        requirement="C# experience",
        requirement_type="required_skill",
        importance="required",
        matched_candidate_claims=[
            CandidateClaim(
                claim="Rust",
                claim_type="skill",
                evidence_source="data/profile/skills.md",
                evidence_excerpt="C# · .NET / ASP.NET Core · Entity Framework Core",
            )
        ],
        status="missing",
        evidence=[],
    )

    result = service._evaluate_requirement(requirement)
    assert result.status == "missing"
    assert result.matched_candidate_claims == []
    assert service._calculate_requirement_score(result) == 0.0


def test_best_match_ranks_jobs_by_score_and_tiebreaker() -> None:
    service = BestMatchService(
        evidence_provider=None,  # type: ignore[arg-type]
        llm=None,  # type: ignore[arg-type]
        repository=None,  # type: ignore[arg-type]
    )

    job_a = BestMatchJobInput(id="job-a", title="Strong Match", description="Need C# and ASP.NET Core")
    job_b = BestMatchJobInput(id="job-b", title="Weaker Match", description="Need React and TypeScript")
    job_c = BestMatchJobInput(id="job-c", title="Same Score", description="Need C# and ASP.NET Core")

    a = service._build_job_result(
        job=job_a,
        requirements=[
            JobRequirement(
                requirement="C#",
                requirement_type="required_skill",
                importance="required",
                matched_candidate_claims=[
                    CandidateClaim(
                        claim="C#",
                        claim_type="skill",
                        evidence_source="data/profile/skills.md",
                        evidence_excerpt="C# · .NET / ASP.NET Core · Entity Framework Core",
                    )
                ],
                status="matched",
                evidence=["C# · .NET / ASP.NET Core · Entity Framework Core"],
            )
        ],
    )
    b = service._build_job_result(
        job=job_b,
        requirements=[
            JobRequirement(
                requirement="React",
                requirement_type="required_skill",
                importance="required",
                matched_candidate_claims=[],
                status="missing",
                evidence=[],
            )
        ],
    )
    c = service._build_job_result(
        job=job_c,
        requirements=[
            JobRequirement(
                requirement="C#",
                requirement_type="required_skill",
                importance="required",
                matched_candidate_claims=[
                    CandidateClaim(
                        claim="C#",
                        claim_type="skill",
                        evidence_source="data/profile/skills.md",
                        evidence_excerpt="C# · .NET / ASP.NET Core · Entity Framework Core",
                    )
                ],
                status="matched",
                evidence=["C# · .NET / ASP.NET Core · Entity Framework Core"],
            )
        ],
    )

    ranked = service._rank_jobs([b, a, c])
    assert [job.job_id for job in ranked] == ["job-a", "job-c", "job-b"]


def test_api_accepts_multiple_jobs() -> None:
    request = BestMatchRequest(
        jobs=[
            BestMatchJobInput(
                id="job-1",
                title="Senior .NET Developer",
                description="We need C# and ASP.NET Core with REST APIs and SQL.",
            ),
            BestMatchJobInput(
                id="job-2",
                title="AI Engineer",
                description="We need agentic AI, RAG, and guardrails experience.",
            ),
        ]
    )

    assert len(request.jobs) == 2
    assert request.jobs[0].id == "job-1"


def test_empty_jobs_request_is_validated() -> None:
    with pytest.raises(ValueError):
        BestMatchRequest(jobs=[])
