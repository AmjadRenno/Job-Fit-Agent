import json
from pathlib import Path

from app.evaluation.metrics import evaluate_case, summarize_metrics
from app.evaluation.models import EvaluationCase
from app.models.job_analysis import JobAnalysisRequest
from app.models.llm_job_analysis import LLMJobAnalysisOutput
from app.services.jobs.analysis import JobAnalysisService
from app.services.profile.evidence import DeterministicCandidateEvidenceProvider
from app.services.profile.repository import FileCandidateProfileRepository


VALID_CLAIMS = {
    "junior-software-developer": ("C#", "C# · .NET / ASP.NET Core · Entity Framework Core"),
    "backend-developer": ("ASP.NET Core", "C# · .NET / ASP.NET Core · Entity Framework Core"),
    "full-stack-developer": ("React / TypeScript", "React / TypeScript · Blazor · JavaScript"),
    "dotnet-developer": ("Blazor", "React / TypeScript · Blazor · JavaScript"),
    "ai-llm-developer": ("LLM application development", "LLM application development · Agentic AI · AI Agents · LangGraph"),
    "agentic-ai-engineer": ("Agentic AI", "LLM application development · Agentic AI · AI Agents · LangGraph"),
    "rag-software-developer": ("RAG", "RAG · Embeddings · Vector databases · MCP (Model Context Protocol)"),
    "cloud-devops-software-developer": ("Docker", "Docker · Testing (xUnit, NUnit, Moq) · Git / GitHub"),
}


def load_cases() -> list[EvaluationCase]:
    dataset_path = Path(__file__).resolve().parents[3] / "data" / "evaluation" / "jobs.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    assert dataset["dataset_version"] == "wave-3.1"
    return [EvaluationCase.model_validate(case) for case in dataset["cases"]]


def test_wave_3_1_offline_evaluation_covers_dataset_and_grounding() -> None:
    repository = FileCandidateProfileRepository(
        Path(__file__).resolve().parents[3] / "data" / "profile"
    )
    evidence_provider = DeterministicCandidateEvidenceProvider(repository)
    metrics = []

    for case in load_cases():
        valid_claim, evidence_excerpt = VALID_CLAIMS[case.id]
        claims = [
            {
                "claim": valid_claim,
                "claim_type": "skill",
                "evidence_source": "data/profile/skills.md",
                "evidence_excerpt": evidence_excerpt,
            }
        ]
        if case.id in {
            "ai-llm-developer",
            "agentic-ai-engineer",
            "rag-software-developer",
            "cloud-devops-software-developer",
        }:
            claims.append(
                {
                    "claim": "Kubernetes",
                    "claim_type": "skill",
                    "evidence_source": "data/profile/skills.md",
                    "evidence_excerpt": "Docker · Testing (xUnit, NUnit, Moq) · Git / GitHub",
                }
            )

        output = LLMJobAnalysisOutput(
            job_summary=case.title,
            matched_candidate_claims=claims,
            missing_requirements=case.expected_missing_requirements,
            analysis="Offline structured-output fixture for contract evaluation.",
        )

        class FixtureLLM:
            def analyze(self, job_description: str, evidence: list[object]) -> LLMJobAnalysisOutput:
                return output

        response = JobAnalysisService(
            evidence_provider=evidence_provider,
            llm=FixtureLLM(),
            repository=repository,
        ).analyze(JobAnalysisRequest(job_description=case.job_description))

        assert response.analysis is not None
        case_metrics = evaluate_case(case, output, response.analysis, repository)
        assert case_metrics.rejected_claims_excluded is True
        assert case_metrics.forbidden_claims_present == []
        assert case_metrics.missing_evidence_behavior == 1.0
        metrics.append(case_metrics)

    summary = summarize_metrics(metrics)

    assert summary.case_count == 8
    assert summary.average_grounding == 0.75
    assert summary.average_relevance == 1.0
    assert summary.average_unsupported_claim_rate == 0.25
    assert summary.average_missing_evidence_behavior == 1.0
    assert summary.average_claim_validation_rate == 0.75
