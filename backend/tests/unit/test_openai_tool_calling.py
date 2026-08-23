from pathlib import Path

import pytest

from app.infrastructure.openai.tool_calling import OpenAIToolCallingJobAnalysisAgent
from app.agent.tools import ToolExecutionError, UnknownToolError
from app.models.llm_job_analysis import LLMJobAnalysisOutput
from app.models.profile import ProfileDocument
from app.models.tools import ToolDefinition


class FakeToolCall:
    type = "function_call"

    def __init__(self, name: str, arguments: str, call_id: str = "call-1") -> None:
        self.name = name
        self.arguments = arguments
        self.call_id = call_id


class FakeResponse:
    def __init__(self, response_id: str, output: list[object], output_parsed=None) -> None:
        self.id = response_id
        self.output = output
        self.output_parsed = output_parsed


class FakeResponses:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = FakeResponses(responses)


class FakeSettings:
    openai_api_key = type("Secret", (), {"get_secret_value": lambda self: "test-key"})()
    openai_model = "test-model"


def document() -> ProfileDocument:
    return ProfileDocument(
        id="skills",
        category="skills",
        source="data/profile/skills.md",
        title="Skills",
        content="C#",
    )


def definition() -> ToolDefinition:
    return ToolDefinition(
        name="search_candidate_evidence",
        description="Search candidate evidence.",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
    )


def final_output() -> LLMJobAnalysisOutput:
    return LLMJobAnalysisOutput(
        job_summary="A grounded result.",
        matched_candidate_claims=[],
        missing_requirements=[],
        analysis="The tool result was considered.",
    )


def test_openai_adapter_executes_function_call_then_continues() -> None:
    client = FakeClient(
        [
            FakeResponse("response-1", [FakeToolCall("search_candidate_evidence", '{"query":"C#"}')]),
            FakeResponse("response-2", [], final_output()),
        ]
    )
    agent = OpenAIToolCallingJobAnalysisAgent(FakeSettings(), client=client, max_iterations=3)
    executed: list[tuple[str, dict[str, object]]] = []

    result = agent.analyze(
        "A job requiring C#.",
        [document()],
        [definition()],
        lambda name, arguments: executed.append((name, arguments)) or {"evidence": ["C#"]},
    )

    assert result.analysis == "The tool result was considered."
    assert executed == [("search_candidate_evidence", {"query": "C#"})]
    assert client.responses.calls[0]["tools"][0]["name"] == "search_candidate_evidence"
    assert client.responses.calls[1]["previous_response_id"] == "response-1"
    assert client.responses.calls[1]["input"][0]["type"] == "function_call_output"


def test_openai_adapter_returns_tool_errors_to_model_without_bypassing_registry() -> None:
    client = FakeClient(
        [
            FakeResponse("response-1", [FakeToolCall("read_filesystem", '{"path":"../../.env"}')]),
            FakeResponse("response-2", [], final_output()),
        ]
    )
    agent = OpenAIToolCallingJobAnalysisAgent(FakeSettings(), client=client)

    result = agent.analyze(
        "A job requiring evidence.",
        [document()],
        [definition()],
        lambda *_: (_ for _ in ()).throw(UnknownToolError("Unknown tool: read_filesystem")),
    )

    assert result.job_summary == "A grounded result."
    output = client.responses.calls[1]["input"][0]["output"]
    assert "Unknown tool" in output
    assert "Unknown tool" in output


def test_openai_adapter_handles_invalid_arguments_and_tool_failures() -> None:
    client = FakeClient(
        [
            FakeResponse("response-1", [FakeToolCall("search_candidate_evidence", '{"query":"../../.env"}')]),
            FakeResponse("response-2", [], final_output()),
        ]
    )
    agent = OpenAIToolCallingJobAnalysisAgent(FakeSettings(), client=client)

    result = agent.analyze(
        "A job requiring evidence.",
        [document()],
        [definition()],
        lambda *_: (_ for _ in ()).throw(ToolExecutionError("Candidate evidence search failed safely.")),
    )

    assert result.job_summary == "A grounded result."
    assert "Candidate evidence search failed safely" in client.responses.calls[1]["input"][0]["output"]


def test_openai_adapter_stops_after_iteration_limit() -> None:
    client = FakeClient(
        [
            FakeResponse(f"response-{index}", [FakeToolCall("search_candidate_evidence", '{"query":"C#"}')])
            for index in range(4)
        ]
    )
    agent = OpenAIToolCallingJobAnalysisAgent(FakeSettings(), client=client, max_iterations=2)

    with pytest.raises(ValueError, match="maximum tool-calling iterations"):
        agent.analyze("A job requiring evidence.", [document()], [definition()], lambda *_: {"evidence": []})
