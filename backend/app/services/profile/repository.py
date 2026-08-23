import re
from pathlib import Path
from typing import Protocol

from app.models.profile import CandidateProfile, ProfileDocument


class CandidateProfileNotFoundError(FileNotFoundError):
    pass


class CandidateProfileRepository(Protocol):
    def get_profile(self) -> ProfileDocument:
        """Return the canonical profile document."""

    def get_skills(self) -> ProfileDocument:
        """Return the canonical skills document."""

    def get_experience(self) -> ProfileDocument:
        """Return the canonical experience document."""

    def get_education(self) -> ProfileDocument:
        """Return the canonical education document."""

    def get_certifications(self) -> ProfileDocument:
        """Return the canonical certifications document."""

    def list_projects(self) -> list[ProfileDocument]:
        """Return project documents in stable filename order."""

    def get_project(self, project_id: str) -> ProfileDocument:
        """Return one project document by its filename stem."""

    def get_candidate_profile(self) -> CandidateProfile:
        """Return all canonical profile documents."""


class FileCandidateProfileRepository:
    _core_documents = {
        "profile": "profile.md",
        "skills": "skills.md",
        "experience": "experience.md",
        "education": "education.md",
        "certifications": "certifications.md",
    }

    def __init__(self, profile_root: Path) -> None:
        self._profile_root = profile_root
        self._projects_root = profile_root / "projects"
        self._repository_root = profile_root.parent.parent

    def get_profile(self) -> ProfileDocument:
        return self._read_core_document("profile")

    def get_skills(self) -> ProfileDocument:
        return self._read_core_document("skills")

    def get_experience(self) -> ProfileDocument:
        return self._read_core_document("experience")

    def get_education(self) -> ProfileDocument:
        return self._read_core_document("education")

    def get_certifications(self) -> ProfileDocument:
        return self._read_core_document("certifications")

    def list_projects(self) -> list[ProfileDocument]:
        if not self._projects_root.is_dir():
            raise CandidateProfileNotFoundError(
                f"Project directory not found: {self._projects_root}"
            )

        return [
            self._read_document(path, "project")
            for path in sorted(self._projects_root.glob("*.md"))
        ]

    def get_project(self, project_id: str) -> ProfileDocument:
        project_path = self._projects_root / f"{project_id}.md"
        if project_path.parent != self._projects_root or not project_path.is_file():
            raise CandidateProfileNotFoundError(
                f"Project not found: {project_id}"
            )
        return self._read_document(project_path, "project")

    def get_candidate_profile(self) -> CandidateProfile:
        return CandidateProfile(
            profile=self.get_profile(),
            skills=self.get_skills(),
            experience=self.get_experience(),
            education=self.get_education(),
            certifications=self.get_certifications(),
            projects=self.list_projects(),
        )

    def _read_core_document(self, document_id: str) -> ProfileDocument:
        return self._read_document(
            self._profile_root / self._core_documents[document_id],
            document_id,
        )

    def _read_document(self, path: Path, category: str) -> ProfileDocument:
        if not path.is_file():
            raise CandidateProfileNotFoundError(f"Profile document not found: {path}")

        content = path.read_text(encoding="utf-8")
        title = next(
            (
                line.removeprefix("# ").strip()
                for line in content.splitlines()
                if line.startswith("# ")
            ),
            path.stem,
        )
        evidence_level = next(
            (
                line.strip()
                for index, line in enumerate(content.splitlines())
                if line.strip().lower() == "## evidence level"
                and index + 1 < len(content.splitlines())
                for line in [content.splitlines()[index + 1]]
            ),
            None,
        )
        evidence_levels = [
            match.group(1).strip()
            for match in re.finditer(r"^## (Tier \d+)\b", content, re.MULTILINE)
        ]
        if evidence_level is not None:
            evidence_levels.append(evidence_level)

        return ProfileDocument(
            id=path.stem,
            category=category,
            source=path.relative_to(self._repository_root).as_posix(),
            title=title,
            content=content,
            evidence_level=evidence_level,
            evidence_levels=evidence_levels,
        )
