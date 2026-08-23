import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.profile import ProfileDocument
from app.services.profile.repository import CandidateProfileRepository


ClaimType = Literal[
    "skill",
    "experience",
    "project",
    "education",
    "certification",
    "other",
]


class CandidateClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str
    claim_type: ClaimType
    evidence_source: str
    evidence_excerpt: str


class GuardrailResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_allowed: bool
    reason_code: str
    message: str


def validate_candidate_claim(
    candidate_claim: CandidateClaim,
    repository: CandidateProfileRepository,
) -> GuardrailResult:
    try:
        evidence = _get_document_by_source(
            repository,
            candidate_claim.evidence_source,
        )
    except (FileNotFoundError, ValueError):
        return GuardrailResult(
            is_allowed=False,
            reason_code="unknown_evidence_source",
            message="The claim references an unknown candidate evidence source.",
        )

    if not _contains(evidence.content, candidate_claim.evidence_excerpt):
        return GuardrailResult(
            is_allowed=False,
            reason_code="evidence_excerpt_not_found",
            message="The supplied evidence excerpt is not present in the source document.",
        )

    claim_supported = _contains(
        candidate_claim.evidence_excerpt,
        candidate_claim.claim,
    ) or _contains(
        candidate_claim.evidence_excerpt,
        _remove_overstated_language(candidate_claim.claim),
    ) or _claim_terms_supported(
        candidate_claim.evidence_excerpt,
        candidate_claim.claim,
    )
    if not claim_supported:
        return GuardrailResult(
            is_allowed=False,
            reason_code="claim_not_supported",
            message="The claim is not directly supported by the supplied evidence excerpt.",
        )

    if _is_course_or_training_source(evidence) and candidate_claim.claim_type == "experience":
        return GuardrailResult(
            is_allowed=False,
            reason_code="course_not_professional_experience",
            message="Course or training evidence cannot support a professional-experience claim.",
        )

    if _is_familiarity_source(evidence, candidate_claim.evidence_excerpt) and _uses_overstated_language(candidate_claim.claim):
        return GuardrailResult(
            is_allowed=False,
            reason_code="evidence_level_overstated",
            message="The claim language exceeds the evidence level in the candidate profile.",
        )

    return GuardrailResult(
        is_allowed=True,
        reason_code="supported_claim",
        message="The claim is traceable to candidate evidence.",
    )


def _get_document_by_source(
    repository: CandidateProfileRepository,
    source: str,
) -> ProfileDocument:
    core_documents = {
        "data/profile/profile.md": repository.get_profile,
        "data/profile/skills.md": repository.get_skills,
        "data/profile/experience.md": repository.get_experience,
        "data/profile/education.md": repository.get_education,
        "data/profile/certifications.md": repository.get_certifications,
    }
    if source in core_documents:
        return core_documents[source]()
    if source.startswith("data/profile/projects/") and source.endswith(".md"):
        return repository.get_project(source.removeprefix("data/profile/projects/").removesuffix(".md"))
    raise ValueError(f"Unsupported evidence source: {source}")


def _contains(container: str, value: str) -> bool:
    return _normalized_content(value) in _normalized_content(container)


def _normalized_content(value: str) -> str:
    return " ".join(value.split()).casefold()


def _is_course_or_training_source(document: ProfileDocument) -> bool:
    if document.category == "certifications":
        return True

    evidence_level = (document.evidence_level or "").casefold()
    return "academic/training-level" in evidence_level or "training-project-level" in evidence_level


def _is_familiarity_source(document: ProfileDocument, evidence_excerpt: str) -> bool:
    if document.category != "skills":
        return False

    sections = re.finditer(
        r"^## (Tier \d+)\b.*?(?=^## |\Z)",
        document.content,
        re.MULTILINE | re.DOTALL,
    )
    return any(
        section.group(1) == "Tier 4"
        and _contains(section.group(0), evidence_excerpt)
        for section in sections
    )


def _uses_overstated_language(claim: str) -> bool:
    overstated_terms = ("advanced", "expert", "professional experience", "senior")
    claim_lower = claim.casefold()
    return any(term in claim_lower for term in overstated_terms)


def _remove_overstated_language(claim: str) -> str:
    cleaned_claim = claim.casefold()
    for term in ("advanced", "expert", "professional experience", "senior"):
        cleaned_claim = cleaned_claim.replace(term, "")
    return " ".join(cleaned_claim.split())


def _claim_terms_supported(evidence_excerpt: str, claim: str) -> bool:
    normalized_claim = _normalize_claim_terms(_strip_generic_prefix(claim))
    if not normalized_claim:
        return False

    evidence_terms = set(_normalize_claim_terms(evidence_excerpt))
    return all(term in evidence_terms for term in normalized_claim)


def _strip_generic_prefix(claim: str) -> str:
    cleaned = claim.casefold().strip()
    prefixes = (
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
    for prefix in prefixes:
        cleaned = re.sub(prefix, "", cleaned)
    return cleaned


def _normalize_claim_terms(value: str) -> list[str]:
    cleaned = value.casefold()
    for separator in ("·", "/", "\\", ",", ";", ":", "(", ")", "[", "]", "{", "}", "-", "–", "—"):
        cleaned = cleaned.replace(separator, " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    stopwords = {
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
    return [token for token in cleaned.split(" ") if token and token not in stopwords]
