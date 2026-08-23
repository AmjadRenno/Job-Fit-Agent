from __future__ import annotations

import json
from copy import deepcopy
from typing import Protocol

from app.models.tools import (
    CandidateEvidenceItem,
    SearchCandidateEvidenceInput,
    SearchCandidateEvidenceResult,
    ToolDefinition,
)
from app.services.profile.evidence import CandidateEvidenceProvider


class ToolError(RuntimeError):
    pass


class UnknownToolError(ToolError):
    pass


class ToolExecutionError(ToolError):
    pass


class SearchCandidateEvidenceTool:
    name = "search_candidate_evidence"
    description = (
        "Search the canonical candidate profile for evidence relevant to a job requirement. "
        "Use only when supplied evidence is insufficient. This returns evidence, not new facts."
    )

    def __init__(self, evidence_provider: CandidateEvidenceProvider) -> None:
        self._evidence_provider = evidence_provider

    def definition(self) -> ToolDefinition:
        schema = _make_openai_strict_schema(SearchCandidateEvidenceInput.model_json_schema())
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=schema,
        )

    def execute(self, arguments: dict[str, object]) -> SearchCandidateEvidenceResult:
        request = SearchCandidateEvidenceInput.model_validate(arguments)
        top_k = request.top_k if request.top_k is not None else 5
        try:
            documents = self._evidence_provider.get_evidence(request.query)
        except Exception as error:
            raise ToolExecutionError("Candidate evidence search failed safely.") from error

        evidence: list[CandidateEvidenceItem] = []
        for document in documents:
            if request.category is not None and document.category != request.category:
                continue
            if request.project_id is not None and document.id != request.project_id:
                continue
            evidence.append(
                CandidateEvidenceItem(
                    source=document.source,
                    title=document.title,
                    category=document.category,
                    project_id=document.id if document.category == "project" else None,
                    evidence_level=document.evidence_level,
                    text=document.content,
                    similarity=getattr(document, "similarity", None),
                )
            )
            if len(evidence) >= top_k:
                break

        return SearchCandidateEvidenceResult(
            tool_name=self.name,
            query=request.query,
            evidence=evidence,
        )


def _make_openai_strict_schema(schema: dict[str, object]) -> dict[str, object]:
    strict_schema = deepcopy(schema)
    properties = strict_schema.get("properties")
    if not isinstance(properties, dict):
        return strict_schema

    strict_schema["required"] = list(properties.keys())
    strict_schema["additionalProperties"] = False
    return strict_schema


class ExecutableTool(Protocol):
    name: str

    def definition(self) -> ToolDefinition:
        ...

    def execute(self, arguments: dict[str, object]) -> object:
        ...


class ToolRegistry:
    def __init__(self, tools: list[ExecutableTool], max_tool_calls: int = 3) -> None:
        if max_tool_calls < 1:
            raise ValueError("max_tool_calls must be positive.")
        self._tools = {tool.name: tool for tool in tools}
        self._max_tool_calls = max_tool_calls
        self._call_count = 0

    def definitions(self) -> list[ToolDefinition]:
        return [tool.definition() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, object]) -> object:
        tool = self._tools.get(name)
        if tool is None:
            raise UnknownToolError(f"Unknown tool: {name}")
        if self._call_count >= self._max_tool_calls:
            raise ToolError("The maximum tool call limit has been reached.")
        self._call_count += 1
        try:
            return tool.execute(arguments)
        except ToolError:
            raise
        except Exception as error:
            raise ToolExecutionError(f"Tool execution failed safely: {name}") from error

    @staticmethod
    def result_for_model(result: object) -> str:
        if hasattr(result, "model_dump_json"):
            return result.model_dump_json()
        return json.dumps(result, ensure_ascii=False)
