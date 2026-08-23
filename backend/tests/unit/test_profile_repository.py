from pathlib import Path

import pytest

from app.services.profile.repository import (
    CandidateProfileNotFoundError,
    FileCandidateProfileRepository,
)


@pytest.fixture
def repository() -> FileCandidateProfileRepository:
    repository_root = Path(__file__).resolve().parents[3]
    return FileCandidateProfileRepository(repository_root / "data" / "profile")


def test_repository_reads_canonical_profile_documents(repository: FileCandidateProfileRepository) -> None:
    profile = repository.get_candidate_profile()

    assert profile.profile.id == "profile"
    assert profile.skills.id == "skills"
    assert profile.education.id == "education"
    assert profile.experience.id == "experience"
    assert profile.certifications.id == "certifications"
    assert len(profile.projects) == 10
    assert [project.id for project in profile.projects] == sorted(
        project.id for project in profile.projects
    )
    assert profile.skills.source == "data/profile/skills.md"
    assert all(project.source == f"data/profile/projects/{project.id}.md" for project in profile.projects)


def test_repository_rejects_unknown_project(repository: FileCandidateProfileRepository) -> None:
    with pytest.raises(CandidateProfileNotFoundError):
        repository.get_project("not-a-real-project")
