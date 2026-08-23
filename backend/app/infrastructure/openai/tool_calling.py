from __future__ import annotations

import json
from collections.abc import Callable
from typing import Protocol

from openai import OpenAI

from app.agent.prompts import JOB_ANALYSIS_SYSTEM_INSTRUCTIONS, build_job_analysis_input
from app.agent.tools import ToolError, ToolRegistry
from app.config import Settings
from app.models.llm_job_analysis import LLMJobAnalysisOutput
from app.models.profile import ProfileDocument
from app.models.tools import ToolDefinition


class ToolCallingJobAnalysisAgent(Protocol):
    def analyze(
        self,
        job_description: str,
        evidence_documents: list[ProfileDocument],
        tool_definitions: list[ToolDefinition],
        execute_tool: Callable[[str, dict[str, object]], object],
    ) -> LLMJobAnalysisOutput:
        ...


class OpenAIToolCallingJobAnalysisAgent:
    def __init__(self, settings: Settings, client: OpenAI | None = None, max_iterations: int = 3) -> None:
        if settings.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is required for tool-using job analysis.")
        if max_iterations < 1:
            raise ValueError("max_iterations must be positive.")

        self._client = client or OpenAI(api_key=settings.openai_api_key.get_secret_value())
        self._model = settings.openai_model
        self._max_iterations = max_iterations

    def analyze(
        self,
        job_description: str,
        evidence_documents: list[ProfileDocument],
        tool_definitions: list[ToolDefinition],
        execute_tool: Callable[[str, dict[str, object]], object],
    ) -> LLMJobAnalysisOutput:
        tools = [definition.as_openai_tool() for definition in tool_definitions]
        response = self._client.responses.parse(
            model=self._model,
            instructions=JOB_ANALYSIS_SYSTEM_INSTRUCTIONS,
            input=build_job_analysis_input(
                job_description,
                [(document.source, document.content) for document in evidence_documents],
            ),
            tools=tools,
            text_format=LLMJobAnalysisOutput,
            parallel_tool_calls=False,
        )

        for _ in range(self._max_iterations):
            if response.output_parsed is not None:
                return response.output_parsed

            tool_calls = [
                item for item in response.output
                if getattr(item, "type", None) == "function_call"
            ]
            if not tool_calls:
                raise ValueError("OpenAI returned neither a final structured result nor a tool call.")

            tool_outputs = []
            for call in tool_calls:
                try:
                    arguments = json.loads(call.arguments)
                    if not isinstance(arguments, dict):
                        raise ValueError("Tool arguments must be a JSON object.")
                    result = execute_tool(call.name, arguments)
                    output = ToolRegistry.result_for_model(result)
                except (json.JSONDecodeError, TypeError, ValueError, ToolError) as error:
                    output = json.dumps({"error": str(error)}, ensure_ascii=False)
                except Exception:
                    output = json.dumps({"error": "Tool execution failed safely."})
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": output,
                    }
                )

            response = self._client.responses.parse(
                model=self._model,
                instructions=JOB_ANALYSIS_SYSTEM_INSTRUCTIONS,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=tools,
                text_format=LLMJobAnalysisOutput,
                parallel_tool_calls=False,
            )

        raise ValueError("The maximum tool-calling iterations were reached without a final result.")
