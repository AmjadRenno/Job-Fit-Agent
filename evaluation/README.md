# Wave 3.1 Evaluation

This evaluation area is separate from `backend/tests/unit/` and evaluates the current Wave 3 job-analysis contract without requiring OpenAI access.

## Dataset

`data/evaluation/jobs.json` is explicitly versioned as `wave-3.1` and contains eight realistic software and AI job descriptions. They are test inputs only and are not candidate facts.

Each case defines expected properties rather than exact LLM wording:

- relevant candidate claim themes
- requirements expected to remain missing
- claims that must not appear as candidate facts

## Offline Method

`backend/tests/evaluation/test_wave_3_1.py` uses structured-output fixtures with the real `JobAnalysisService`, `CandidateProfileRepository`, and existing guardrails. It evaluates raw model-proposed claims before and after validation.

The test does not call OpenAI. The offline result evaluates the application grounding boundary and metric calculations, not live model intelligence or prompt quality.

## Metrics

- **Grounding**: validated raw candidate claims divided by raw candidate claims.
- **Relevance**: approved claims matching an expected relevant claim theme divided by approved claims.
- **Unsupported-claim rate**: rejected raw candidate claims divided by raw candidate claims.
- **Missing-evidence behavior**: expected missing requirements represented in the final result.
- **Claim validation rate**: approved raw candidate claims divided by raw candidate claims.

Wave 4 adds a comparison evaluation under `backend/tests/evaluation/test_wave_4_rag.py`. It verifies that retrieval reduces the evidence scope versus whole-profile selection while preserving canonical source and excerpt traceability. The fixture is deterministic and does not claim to measure live embedding quality.
