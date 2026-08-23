from pathlib import Path
import json

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from app.agent.tools import (
    SearchCandidateEvidenceTool,
    ToolRegistry,
    UnknownToolError,
)
from app.api.dependencies import get_job_analysis_service
from app.main import app
from app.models.profile import ProfileDocument
from app.models.llm_job_analysis import LLMJobAnalysisOutput
from app.models.tools import SearchCandidateEvidenceInput
from app.services.jobs.analysis import JobAnalysisService
from app.services.profile.repository import FileCandidateProfileRepository


class FakeEvidenceProvider:
    def __init__(self, documents: list[ProfileDocument]) -> None:
        self.documents = documents
        self.queries: list[str] = []

    def get_evidence(self, query: str) -> list[ProfileDocument]:
        self.queries.append(query)
        return self.documents


class FakeToolAgent:
    def __init__(self, tool_name: str = "search_candidate_evidence") -> None:
        self.tool_name = tool_name
        self.calls = 0

    def analyze(self, job_description, evidence_documents, tool_definitions, execute_tool):
        del evidence_documents, tool_definitions
        self.calls += 1
        result = execute_tool(
            self.tool_name,
            {"query": "C#", "category": "skills", "top_k": 2},
        )
        assert result.evidence
        return type(
            "Output",
            (),
            {
                "job_summary": "A C# role.",
                "matched_candidate_claims": [],
                "missing_requirements": [],
                "analysis": f"Tool returned {len(result.evidence)} evidence item(s).",
            },
        )()


@pytest.fixture
def repository() -> FileCandidateProfileRepository:
    root = Path(__file__).resolve().parents[3]
    return FileCandidateProfileRepository(root / "data" / "profile")


def test_search_tool_validates_inputs_and_rejects_path_access(repository: FileCandidateProfileRepository) -> None:
    document = repository.get_skills()
    provider = FakeEvidenceProvider([document])
    tool = SearchCandidateEvidenceTool(provider)

    query_only = SearchCandidateEvidenceInput(query="C#")
    with_category = SearchCandidateEvidenceInput(query="C#", category="skills")
    with_project = SearchCandidateEvidenceInput(query="C#", project_id="portfolio")
    with_null_optionals = SearchCandidateEvidenceInput(
        query="C#",
        category=None,
        project_id=None,
        top_k=None,
    )

    assert query_only.query == "C#"
    assert with_category.category == "skills"
    assert with_project.project_id == "portfolio"
    assert with_null_optionals.category is None
    assert with_null_optionals.project_id is None
    assert with_null_optionals.top_k is None

    result = tool.execute({"query": "C#", "category": "skills", "top_k": 2})
    assert result.tool_name == "search_candidate_evidence"
    assert result.evidence[0].source == "data/profile/skills.md"
    assert result.evidence[0].text == document.content
    assert provider.queries == ["C#"]

    null_result = tool.execute(
        {"query": "C#", "category": None, "project_id": None, "top_k": None}
    )
    assert null_result.evidence[0].source == "data/profile/skills.md"
    assert provider.queries == ["C#", "C#"]

    with pytest.raises(ValidationError):
        SearchCandidateEvidenceInput(query="../secrets", project_id="../../.env")
    with pytest.raises(ValidationError):
        SearchCandidateEvidenceInput(query="C#", extra_field="nope")
    with pytest.raises(ValidationError):
        SearchCandidateEvidenceInput(query="C#", project_id=".env")
    with pytest.raises(ValidationError):
        SearchCandidateEvidenceInput.model_validate({})


def test_tool_registry_rejects_unknown_tools(repository: FileCandidateProfileRepository) -> None:
    registry = ToolRegistry([SearchCandidateEvidenceTool(FakeEvidenceProvider([repository.get_skills()]))])

    with pytest.raises(UnknownToolError):
        registry.execute("read_filesystem", {"path": "../../.env"})

    definition = registry.definitions()[0]
    assert definition.name == "search_candidate_evidence"
    assert definition.parameters["additionalProperties"] is False
    assert definition.parameters["required"] == ["query", "category", "project_id", "top_k"]
    assert definition.parameters["properties"]["query"]["type"] == "string"
    assert definition.parameters["properties"]["category"]["anyOf"][1]["type"] == "null"
    assert definition.parameters["properties"]["project_id"]["anyOf"][1]["type"] == "null"
    assert definition.parameters["properties"]["top_k"]["anyOf"][1]["type"] == "null"


def test_search_tool_handles_empty_results_without_inventing_evidence() -> None:
    tool = SearchCandidateEvidenceTool(FakeEvidenceProvider([]))

    result = tool.execute({"query": "Kubernetes", "top_k": 3})

    assert result.evidence == []


def test_tool_using_job_analysis_executes_real_tool_and_keeps_service_grounding(repository: FileCandidateProfileRepository) -> None:
    provider = FakeEvidenceProvider([repository.get_skills()])
    registry = ToolRegistry([SearchCandidateEvidenceTool(provider)])
    agent = FakeToolAgent()
    service = JobAnalysisService(
        evidence_provider=provider,
        llm=None,  # type: ignore[arg-type]
        repository=repository,
        tool_agent=agent,
        tool_registry=registry,
    )

    response = service.analyze(
        type(
            "Request",
            (),
            {"job_description": "We need a backend developer with C# and REST APIs for our team."},
        )()
    )

    assert response.status == "analyzed"
    assert agent.calls == 1
    assert provider.queries == [
        "We need a backend developer with C# and REST APIs for our team.",
        "C#",
    ]


def test_tool_result_cannot_authorize_unsupported_candidate_claim(repository: FileCandidateProfileRepository) -> None:
    provider = FakeEvidenceProvider([repository.get_skills()])
    registry = ToolRegistry([SearchCandidateEvidenceTool(provider)])

    class ClaimProducingAgent(FakeToolAgent):
        def analyze(self, job_description, evidence_documents, tool_definitions, execute_tool):
            result = execute_tool("search_candidate_evidence", {"query": "C#"})
            return LLMJobAnalysisOutput(
                job_summary="A role requiring evidence.",
                matched_candidate_claims=[
                    {
                        "claim": "Kubernetes",
                        "claim_type": "skill",
                        "evidence_source": result.evidence[0].source,
                        "evidence_excerpt": result.evidence[0].text,
                    }
                ],
                missing_requirements=[],
                analysis="The tool result was checked.",
            )

    service = JobAnalysisService(
        evidence_provider=provider,
        llm=None,  # type: ignore[arg-type]
        repository=repository,
        tool_agent=ClaimProducingAgent(),
        tool_registry=registry,
    )
    response = service.analyze(
        type(
            "Request",
            (),
            {"job_description": "We need a backend developer with C# and REST APIs for our team."},
        )()
    )

    assert response.analysis is not None
    assert response.analysis.matched_candidate_claims == []
    assert response.analysis.grounding_warnings


def test_tool_call_limit_and_tool_failure_are_typed(repository: FileCandidateProfileRepository) -> None:
    provider = FakeEvidenceProvider([repository.get_skills()])
    tool = SearchCandidateEvidenceTool(provider)
    registry = ToolRegistry([tool], max_tool_calls=1)
    first = registry.execute("search_candidate_evidence", {"query": "C#"})
    assert first.evidence
    with pytest.raises(RuntimeError, match="maximum tool call"):
        registry.execute("search_candidate_evidence", {"query": "REST APIs"})


def test_tool_driven_job_analysis_endpoint_uses_application_registry(repository: FileCandidateProfileRepository) -> None:
    provider = FakeEvidenceProvider([repository.get_skills()])
    registry = ToolRegistry([SearchCandidateEvidenceTool(provider)])
    service = JobAnalysisService(
        evidence_provider=provider,
        llm=None,  # type: ignore[arg-type]
        repository=repository,
        tool_agent=FakeToolAgent(),
        tool_registry=registry,
    )
    app.dependency_overrides[get_job_analysis_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/job-analysis",
                json={
                    "job_description": "We need a backend developer with C# and REST APIs for our team."
                },
            )
        assert response.status_code == 200
        assert response.json()["status"] == "analyzed"
    finally:
        app.dependency_overrides.clear()


def test_wave_7_evaluation_dataset_covers_required_tool_scenarios() -> None:
    dataset_path = Path(__file__).resolve().parents[3] / "data" / "evaluation" / "wave-7-tool-calls.json"
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = payload["cases"]
    assert len(cases) == 7
    assert any(case["expected_tool"] is None for case in cases)
    assert any(case["expected_outcome"] == "safe_tool_failure" for case in cases)
    assert any(case["expected_outcome"] == "rejected_claim" for case in cases)
