# Agent Specification

## Status

Implemented as a request-scoped, bounded workflow. There is no persistent LangGraph graph, no multi-agent runtime, and no autonomous background agent.

## Goal

Analyze one job description against one candidate profile, explain the fit and gaps, and generate a grounded cover letter when requested. The user can review the returned evidence and execution trace in the frontend.

## Runtime Shape

`Job input -> API -> application services -> RAG / bounded tool use -> LLM -> guardrails -> deterministic result -> frontend`

The workflow is request-scoped. Each frontend action creates one Run ID, passes it through the API, and receives the same Run ID in the returned execution trace.

## Responsibilities

- Deterministic validation handles empty or too-short job descriptions.
- Job Analysis returns structured output and candidate claims only after guardrails.
- Best Match owns deterministic scoring, ranking, and critical-gap detection.
- Cover Letter uses approved claims only for final prose.
- The frontend only calls the existing API and renders the returned result.

## Tool Calling Contract

The only allowlisted tool is `search_candidate_evidence`.

Input is strict and typed:

- `query`: required string with bounded length
- `category`: optional canonical profile category
- `project_id`: optional safe project identifier
- `top_k`: bounded integer from 1 to 10

The tool returns traceable evidence items containing source, title, category, project ID when applicable, evidence level, exact evidence text, and similarity when available. It delegates to the existing `CandidateEvidenceProvider` and cannot access OpenAI, arbitrary files, paths, secrets, or environment variables.

The `ToolRegistry` is the only application execution boundary. Unknown tools, malformed arguments, extra arguments, path-like values, `.env` references, and secret or environment requests are rejected. Each request receives a fresh registry with a maximum of three tool calls.

The OpenAI Responses adapter handles the real loop:

`LLM response -> function_call -> registry validation/execution -> function_call_output -> LLM continuation -> structured output`

The adapter stops when a final structured result is parsed or returns a typed failure after the iteration limit. Tool errors are not treated as candidate facts.

## Grounding Contract

Any candidate-related text must follow this flow:

`Retrieval -> Candidate Claims -> validate_candidate_claim(...) -> Approved Claims -> Final text`

### Atomic Candidate Claims

The LLM returns short, atomic claims. Each claim must be one simple factual assertion about the candidate, such as a skill, project, education fact, certification, or experience fact. Claims are evidence references, not complete marketing sentences.

### Validation Boundary

Every candidate claim must pass `validate_candidate_claim(...)` before it can be used as factual candidate content. Only claims with `is_allowed == True` may be used to construct candidate-facing or employer-facing natural language.

### Missing Evidence and Prohibited Upgrades

If the candidate profile does not contain sufficient evidence for a claim, the system omits the claim or explicitly represents missing evidence or uncertainty. It must never upgrade:

- course into professional experience
- academic project into professional experience
- familiarity into advanced expertise
- basic knowledge into expert knowledge

## Architectural Principle

> The LLM is a reasoning and generation component, not the source of truth for candidate facts.

The candidate profile and retrieved evidence remain the authoritative source for candidate claims.

## Non-Goals

MCP, A2A, LangGraph, streaming, multi-agent orchestration, CV generation, browser automation, automatic applications, and Chrome extensions are out of scope.
