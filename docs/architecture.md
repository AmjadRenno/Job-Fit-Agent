# Architecture

## Purpose

Job Fit Agent evaluates one job description against a canonical candidate profile and produces grounded analysis, deterministic fit scoring, and a cover letter built only from approved claims. A React frontend exposes the workflow and shows the real execution trace returned by the backend.

## System Overview

Frontend -> API -> Application Services -> Agent / RAG / Guardrails -> OpenAI / Evidence Provider -> Grounded Result

The backend routes are thin. Application services own orchestration and validation. Infrastructure owns OpenAI, RAG, and storage adapters. The frontend only calls the existing API and renders the returned result and trace.

## Runtime Flow

### Job Analysis

1. Validate the job description.
2. Retrieve candidate evidence through the RAG provider or the bounded evidence tool.
3. Let the LLM interpret the job and propose atomic candidate claims.
4. Validate every candidate claim with `validate_candidate_claim(...)`.
5. Return grounded analysis, approved claims, missing requirements, and execution trace data.

### Best Match

1. Retrieve candidate evidence for the job description.
2. Extract requirements with the LLM when available.
3. Classify each requirement as required, preferred, or unknown.
4. Validate candidate claims before they contribute to scoring.
5. Compute a deterministic 0-100 score and critical gaps.

### Cover Letter

1. Retrieve candidate evidence.
2. Build a grounded match summary.
3. Ask the LLM for atomic candidate claims.
4. Validate each claim.
5. Render the final letter only from approved claims.

### Execution Trace

`ExecutionTraceRecorder` captures real step names, statuses, and durations around the application work. The same Run ID is carried from the frontend into the backend responses so the UI can display the actual run that produced the result.

## Boundaries

- **Domain**: Pure business concepts and deterministic rules.
- **Application / services**: Use cases and orchestration-facing interfaces.
- **Infrastructure**: OpenAI adapters, RAG, persistence, and tracing helpers.
- **API**: FastAPI routes and dependency injection only.
- **Frontend**: React/Vite UI that calls the API and renders returned data.
- **Agent**: The bounded `search_candidate_evidence` function-calling path only.

## Grounding

Canonical candidate evidence -> Retrieval -> Candidate Claims -> Guardrails -> Approved Claims -> User-facing grounded output

Approved claims are the source of truth for candidate facts. The LLM is not the final authority for candidate facts or the numeric match score.

## Tool Calling

The only allowlisted tool is `search_candidate_evidence`.

- validated inputs
- bounded calls
- traceable evidence output
- still subject to the existing guardrails

The tool delegates to the existing `CandidateEvidenceProvider`. It does not access secrets, arbitrary files, or environment variables.

## Reliability and Security

- input validation
- tool allowlist
- bounded tool calls
- path and environment protection
- grounding guardrails
- deterministic scoring
- tests

## Evaluation and Testing

The repository includes offline evaluation fixtures and regression tests for grounding, RAG retrieval, Best Match scoring, cover-letter grounding, and bounded function calling. The live OpenAI happy path is still subject to external account/billing availability.

## Non-Goals

The current implementation does not add MCP, A2A, LangGraph, multi-agent orchestration, streaming, or autonomous application submission.
