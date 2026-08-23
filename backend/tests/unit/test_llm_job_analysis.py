from types import SimpleNamespace

from app.config import Settings
from app.infrastructure.openai.job_analysis import OpenAIJobAnalysisLLM
from app.models.llm_job_analysis import LLMJobAnalysisOutput
from app.models.profile import ProfileDocument


def test_structured_llm_output_parses_atomic_claims() -> None:
    output = LLMJobAnalysisOutput.model_validate(
        {
            "job_summary": "Backend role",
            "matched_candidate_claims": [
                {
                    "claim": "C#",
                    "claim_type": "skill",
                    "evidence_source": "data/profile/skills.md",
                    "evidence_excerpt": "C# · .NET / ASP.NET Core · Entity Framework Core",
                }
            ],
            "missing_requirements": ["Kubernetes"],
            "analysis": "The evidence supports backend development.",
        }
    )

    assert output.matched_candidate_claims[0].claim == "C#"
    assert output.missing_requirements == ["Kubernetes"]


def test_openai_adapter_uses_responses_parse_with_mocked_client() -> None:
    expected = LLMJobAnalysisOutput(
        job_summary="Backend role",
        matched_candidate_claims=[],
        missing_requirements=[],
        analysis="Insufficient evidence.",
    )

    class FakeResponses:
        def __init__(self) -> None:
            self.arguments: dict[str, object] = {}

        def parse(self, **kwargs: object) -> SimpleNamespace:
            self.arguments = kwargs
            return SimpleNamespace(output_parsed=expected)

    fake_responses = FakeResponses()
    fake_client = SimpleNamespace(responses=fake_responses)
    settings = Settings(openai_api_key="test-key", openai_model="test-model")
    adapter = OpenAIJobAnalysisLLM(settings, client=fake_client)  # type: ignore[arg-type]
    document = ProfileDocument(
        id="skills",
        category="skills",
        source="data/profile/skills.md",
        title="Skills",
        content="C#",
    )

    result = adapter.analyze("Backend job", [document])

    assert result == expected
    assert fake_responses.arguments["model"] == "test-model"
    assert fake_responses.arguments["text_format"] is LLMJobAnalysisOutput
    assert "data/profile/skills.md" in str(fake_responses.arguments["input"])


def test_openai_adapter_requires_api_key() -> None:
    try:
        OpenAIJobAnalysisLLM(Settings(openai_api_key=None))
    except ValueError as error:
        assert str(error) == "OPENAI_API_KEY is required for LLM-backed job analysis."
    else:
        raise AssertionError("Expected missing API key to be rejected")