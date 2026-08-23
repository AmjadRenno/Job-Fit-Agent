# Progress Log

## 2026-08-19 | Wave 1

### What was implemented

- Created the initial repository structure for the Python backend.
- Added environment-backed Pydantic settings.
- Added a minimal FastAPI application with a `/health` endpoint.
- Added clean boundaries for API routes, application services, domain values, and infrastructure logging.
- Added one unit test for the health endpoint.
- Added project documentation and repository hygiene files.

### Files and folders created or changed

- `backend/app/` with `config.py`, `main.py`, domain, services, infrastructure logging, and API route packages.
- `backend/tests/unit/test_health.py`.
- `backend/requirements.txt`.
- `.env.example`, `.gitignore`, `README.md`.
- `docs/architecture.md`, `docs/agent-spec.md`.
- `progress-log.md`.

### Important architectural decisions

- API routes remain thin and do not contain business logic or provider calls.
- The health path uses dependency injection from the API route to an application service and a framework-independent domain value.
- Provider integrations and agent orchestration are deferred until their dedicated waves.
- Configuration is loaded from environment variables through `pydantic-settings`; secrets are not stored in source.

### Technologies introduced

- Python 3.11 runtime used for validation.
- FastAPI, Pydantic, `pydantic-settings`, Uvicorn, HTTPX, and pytest.
- Python standard `logging`.

### Tests and checks performed

- Created `backend/.venv` and installed `backend/requirements.txt`.
- Ran `python -m pytest` from `backend/`: 1 test passed.
- The endpoint was exercised through FastAPI `TestClient` at `/health`.
- Started Uvicorn on port `8017` and verified `GET /health` over HTTP: `200` with the expected JSON response.

### Current project status

Wave 1 foundation is implemented and locally testable. No LangGraph, OpenAI, RAG, Qdrant, MCP, cover-letter generation, evaluation framework, frontend, Docker, CI, or deployment code exists yet.

### Next planned step

Wave 2: define the job-analysis domain/application contract and deterministic job validation, after approval.

### Known issues or technical debt

- Dependency versions are bounded but not lock-pinned yet.
- Structured request/response schemas and production request logging will be added with the first real API use case.
- The current logging setup is intentionally basic and does not yet attach agent run or node metadata.
- The current FastAPI/Starlette test stack emits a non-failing deprecation warning recommending a future `httpx2` package.

## 2026-08-19 | Wave 2

### What was implemented

- Added deterministic job-description validation with whitespace normalization, empty-input handling, and a 50-character minimum.
- Added Pydantic request, validation-response, semantic-analysis, and top-level job-analysis response models.
- Added the `JobAnalysisUseCase` application protocol and a deterministic implementation that validates input without calling an LLM.
- Added unit tests for validation edge cases and the application response contract.

### Files and folders created or changed

- `backend/app/domain/job_validation.py`.
- `backend/app/models/job_analysis.py` and `backend/app/models/__init__.py`.
- `backend/app/services/jobs/analysis.py` and `backend/app/services/jobs/__init__.py`.
- `backend/tests/unit/test_job_validation.py`.
- `backend/tests/unit/test_job_analysis_service.py`.
- `docs/architecture.md`, `docs/agent-spec.md`, and `README.md`.
- `progress-log.md`.

### Important architectural decisions

- Validation remains a pure domain function and has no Pydantic, FastAPI, or provider dependency.
- The application service explicitly maps the domain dataclass to the Pydantic response model at the boundary.
- The structured semantic `JobAnalysis` payload is optional and remains empty in Wave 2; no deterministic placeholder analysis is presented as real LLM analysis.
- No API route was added because this wave establishes the use-case contract before exposing an HTTP workflow.

### Technologies introduced

- Pydantic models with strict extra-field handling for the job-analysis contract.
- Python `Protocol` for the application use-case boundary.

### Tests and checks performed

- Focused Wave 2 tests: 6 passed.
- Full test suite: 7 passed with one existing non-failing deprecation warning.
- Started Uvicorn on port `8018` and verified `GET /health`: `200` with the expected JSON response.
- Application diagnostics reported no errors, and no real `.env` file was found.

### Current project status

Wave 2 deterministic foundation is implemented. OpenAI, LangGraph, RAG, Qdrant, MCP, cover-letter generation, frontend, Docker, CI, deployment, and evaluation remain deferred.

### Next planned step

Wave 3: implement LLM-backed job analysis behind the existing application contract, after approval.

### Known issues or technical debt

- The 50-character minimum is an initial product rule and may need adjustment based on real job-description samples.
- Semantic analysis fields are defined but intentionally not populated until the LLM wave.
- The existing non-failing FastAPI/Starlette `httpx2` deprecation warning remains.

## 2026-08-19 | Wave 2 follow-up

### What was implemented

- Confirmed that `backend/app/domain/health.py` was only a transport dataclass with no business logic.
- Removed the redundant health domain and service layers; `/health` now returns its small status payload directly from the API route using injected settings.
- Replaced the ambiguous `qualifications` field in `JobAnalysis` with explicit `experience_level`, `education`, and `location` fields.
- Added a unit test covering the new structured fields.

### Files and folders created or changed

- Deleted `backend/app/domain/health.py`.
- Deleted `backend/app/services/health.py`.
- Changed `backend/app/api/routes/health.py`.
- Changed `backend/app/models/job_analysis.py`.
- Changed `backend/tests/unit/test_job_analysis_service.py`.
- Changed `docs/architecture.md`, `docs/agent-spec.md`, and `progress-log.md`.

### Tests and checks performed

- Focused and full tests: 8 passed with the existing non-failing Starlette/httpx deprecation warning.

### Current project status

Wave 2 remains complete. Wave 3 has not started because the repository does not contain the user's profile data required to create truthful candidate evidence.

### Next planned step

Receive the user's real profile content, create `data/profile/cv.md`, `skills.md`, and `projects/`, then begin Wave 3 with profile retrieval feeding the LLM analysis node.

### Known issues or technical debt

- No profile files were created because inventing candidate information would violate the project's grounding requirement.

## 2026-08-20 | Candidate Profile Infrastructure

### What was implemented

- Read all candidate source documents that were present at the repository root, including the five core documents and all ten project documents.
- Reorganized the unchanged source documents under the canonical `data/profile/` structure.
- Added typed profile document models and a `CandidateProfileRepository` application protocol.
- Added `FileCandidateProfileRepository` as the filesystem implementation for core documents and projects.
- Added structured candidate claims and deterministic guardrails for source traceability, unsupported claims, course-versus-experience boundaries, and Tier 4/familiarity overstatement.
- Kept AI, RAG, embeddings, Qdrant, MCP, and Wave 3 out of scope.

### Files and folders discovered

- `data/profile/profile.md`
- `data/profile/skills.md`
- `data/profile/education.md`
- `data/profile/experience.md`
- `data/profile/certifications.md`
- `data/profile/projects/medcom-ai-guide.md`
- `data/profile/projects/godkendelsesoversigt.md`
- `data/profile/projects/dentalclinic-microservices.md`
- `data/profile/projects/supplybase.md`
- `data/profile/projects/eco-tasks-airguard.md`
- `data/profile/projects/tana.md`
- `data/profile/projects/edc.md`
- `data/profile/projects/scooterland.md`
- `data/profile/projects/umbraco.md`
- `data/profile/projects/portfolio.md`

The files originally existed at the repository root. They were moved without factual edits, and the old root copies were deleted to prevent competing sources of truth.

### Files created or changed

- Created `data/profile/` and its ten unchanged Markdown source documents.
- Deleted the fifteen old root-level profile/project Markdown copies.
- Created `backend/app/models/profile.py`.
- Created `backend/app/services/profile/repository.py` and its package initializer.
- Created `backend/app/agent/guardrails.py` and its package initializer.
- Created `backend/tests/unit/test_profile_repository.py`.
- Created `backend/tests/unit/test_guardrails.py`.
- Updated `docs/architecture.md`, `docs/agent-spec.md`, `README.md`, and `progress-log.md`.

### Important architectural decisions

- Candidate facts remain data; repository access and guardrails remain application logic.
- The application depends on a protocol, while filesystem access is isolated in `FileCandidateProfileRepository`.
- Project lookup is by filename stem, so adding a project requires one new Markdown document.
- No synthetic metadata was added. IDs, source paths, titles, categories, and evidence-level values are derived from existing files and paths.
- A claim is allowed only when its source is canonical, its excerpt exists in that source, and its claim is supported by the excerpt.
- Certification/course/training evidence cannot be used as professional experience, and Tier 4/familiarity evidence cannot support inflated expertise language.

### Candidate-fact review

- All ten project files and all five core documents were readable.
- No direct contradictory candidate facts were found during this review.
- No candidate facts, technologies, dates, achievements, or language levels were invented or rewritten.

### Tests and checks performed

- Focused profile and guardrail tests: 10 passed.
- Repository test confirms all five core documents and ten projects load from `data/profile/`.
- Guardrail tests cover supported claims, unsupported skills/experience/projects/education, course-only evidence, unknown evidence, and inflated Tier 4 claims.
- Full pytest suite: 18 passed with one existing non-failing Starlette/httpx deprecation warning.
- All 15 profile Markdown files were verified readable and non-empty.
- Imports succeeded; the repository loaded all 10 projects.
- FastAPI started on port `8019`, and `GET /health` returned `200` with the expected JSON response.
- No competing root-level profile copies remain.
- Rechecked the moved MedCom.AIGuide source after restoring its original Burp Suite security-testing detail: profile source check passed.

## 2026-08-20 | Wave 3

### What was implemented

- Added environment-backed `OPENAI_API_KEY` and configurable `OPENAI_MODEL` settings.
- Added the official OpenAI Python SDK and an `OpenAIJobAnalysisLLM` adapter using the Responses API structured parsing path.
- Added `LLMJobAnalysisOutput` with job summary, atomic candidate claims, missing requirements, and analysis.
- Added `CandidateEvidenceProvider` and a deterministic implementation that selects the canonical profile documents through the existing repository.
- Replaced the deterministic job-analysis placeholder with `JobAnalysisService`.
- Added a thin `POST /job-analysis` route with dependency injection.
- Added a versionable prompt layer that distinguishes job requirements from candidate evidence and prohibits unsupported or exaggerated claims.
- Claims are validated through the existing `validate_candidate_claim(...)`; approved claims enter final analysis, while rejected claim text is excluded and represented only by a generic `grounding_warnings` message.

### Files created or changed

- Changed `backend/app/config.py`, `backend/requirements.txt`, `.env.example`, and `backend/app/main.py`.
- Created `backend/app/models/llm_job_analysis.py`.
- Changed `backend/app/models/job_analysis.py`.
- Created `backend/app/services/profile/evidence.py`.
- Changed `backend/app/services/jobs/analysis.py`.
- Created `backend/app/agent/prompts.py`.
- Created `backend/app/infrastructure/openai/__init__.py` and `backend/app/infrastructure/openai/job_analysis.py`.
- Created `backend/app/api/dependencies.py` and `backend/app/api/routes/job_analysis.py`.
- Changed `backend/tests/unit/test_job_analysis_service.py`.
- Created `backend/tests/unit/test_llm_job_analysis.py`.
- Updated `docs/architecture.md`, `docs/agent-spec.md`, `README.md`, and `progress-log.md`.

### Important architectural decisions

- The application depends on `JobAnalysisLLM` and `CandidateEvidenceProvider` protocols; OpenAI and filesystem selection remain replaceable infrastructure/application implementations.
- The current evidence provider is deterministic and uses the full canonical profile set. It is not semantic RAG and does not use embeddings or Qdrant.
- Structured LLM claims reuse the existing `CandidateClaim` model. No competing grounding model was introduced.
- Guardrails remain unchanged. The service excludes rejected claims from `matched_candidate_claims` and does not expose their claim text in final output.
- The API route contains no business logic or direct provider invocation.

### Tests and checks performed

- Focused Wave 3 tests: 7 passed.
- Full pytest suite: 26 passed with one existing non-failing Starlette/httpx deprecation warning.
- Diagnostics reported no errors.
- OpenAPI import check confirmed `/health` and `/job-analysis`.
- Uvicorn started on port `8020`; `GET /health` returned `200` with the expected JSON response.
- No real `.env` file was found outside the ignored virtual environment.
- Normal tests used a mocked OpenAI client; no live API call was made.
- Follow-up grounding check: rejected claim text is absent from final analysis; only a generic `grounding_warnings` message is returned when needed. Focused service tests and full suite remained green: 26 passed.
- OpenAI adapter tests use a mocked client; no live API call is required by normal tests.

### Current project status

Wave 3 LLM-backed Job Analysis is implemented. No RAG, embeddings, vector database, MCP, LangGraph graph, cover-letter generation, frontend, Docker, CI, or deployment was added.

### Next planned step

Wave 4: evaluate and improve the grounded job-analysis workflow, then consider semantic retrieval only if the evaluation shows deterministic whole-profile evidence is insufficient.

### Known limitations or technical debt

- The deterministic evidence provider passes the complete profile to the LLM; semantic retrieval is intentionally deferred.
- Current claim validation remains conservative literal evidence/excerpt matching rather than semantic entailment.
- A missing `OPENAI_API_KEY` causes the injected OpenAI adapter to reject job-analysis requests; health and non-LLM tests remain available.
- The existing non-failing Starlette/httpx deprecation warning remains.

## 2026-08-20 | Wave 3.1 Evaluation

### What was implemented

- Added a versioned dataset of eight realistic software and AI job descriptions under `data/evaluation/jobs.json`.
- Added expected behavior properties for relevant evidence, missing requirements, and forbidden candidate claims without fabricating candidate qualifications.
- Added a separate evaluation model and metrics layer under `backend/app/evaluation/`.
- Added an isolated evaluation test under `backend/tests/evaluation/test_wave_3_1.py` using mocked structured LLM outputs and the real service/repository/guardrails.
- Added a human-readable report at `evaluation/reports/wave-3.1-report.md` and methodology documentation at `evaluation/README.md`.
- Connected the lifecycle to `LLM -> evaluation -> improvement` in the architecture, agent specification, and README.

### Evaluation methodology

Each case passes through the real Wave 3 service. The evaluator compares raw model-proposed claims with guardrail-approved final claims and computes grounding, relevance, unsupported-claim rate, missing-evidence behavior, and claim validation rate. Four cases intentionally include an unsupported Kubernetes claim to verify rejection and exclusion.

### Results

- Evaluation test: 1 passed.
- Dataset cases: 8.
- Dataset version: `wave-3.1`.
- Average grounding: 0.75.
- Average relevance: 1.00 for the offline fixture.
- Average unsupported-claim rate: 0.25 in the intentionally adversarial raw fixtures.
- Average missing-evidence behavior: 1.00.
- Average claim validation rate: 0.75.
- Forbidden claims in final results: 0.
- Rejected claims excluded from final results: 8/8 cases.

### Important failures and findings

- The 0.25 raw unsupported-claim rate is expected from four intentionally invalid fixture claims; all were rejected before final output.
- This is not a live OpenAI quality benchmark because no API call was made.
- Whole-profile deterministic evidence selection remains broad and may reduce relevance in real jobs.
- Literal claim validation remains conservative and can reject natural-language claims requiring semantic entailment.
- No attempt was made to solve these limitations in Wave 3.1.

### Files created or changed

- Created `data/evaluation/jobs.json`.
- Created `backend/app/evaluation/__init__.py`, `backend/app/evaluation/models.py`, and `backend/app/evaluation/metrics.py`.
- Created `backend/tests/evaluation/__init__.py` and `backend/tests/evaluation/test_wave_3_1.py`.
- Created `evaluation/README.md` and `evaluation/reports/wave-3.1-report.md`.
- Updated `docs/architecture.md`, `docs/agent-spec.md`, `README.md`, and `progress-log.md`.

### Current project status

Wave 3.1 Evaluation is complete. Wave 4 has not started. RAG, embeddings, Qdrant, MCP, and LangGraph remain deferred.

### Next planned step

Wave 4 should decide how to improve evidence selection and claim validation based on these findings, after review and approval.

### Known limitations or technical debt

- Evaluation fixtures use mocked LLM outputs and do not measure live model quality, latency, or cost.
- No opt-in live evaluation command was added; ordinary pytest never requires `OPENAI_API_KEY`.
- Metric relevance is a lightweight expected-theme comparison, not a semantic ranking benchmark.

### Final validation

- Full pytest suite: 27 passed with one existing non-failing Starlette/httpx deprecation warning.
- Unit tests remain separate: 26 collected under `tests/unit/`.
- Evaluation tests remain separate: 1 collected under `tests/evaluation/`.
- FastAPI started on port `8021`; `GET /health` returned `200`.
- Diagnostics reported no errors.
- No real `.env` file or committed secret was found.
- Final versioned dataset check: `wave-3.1`, 8 cases.

## 2026-08-20 | Guardrail review follow-up

### What was clarified and changed

- Confirmed that literal claim matching is an intentional temporary conservative constraint. A generated natural-language claim must currently appear directly in its evidence excerpt, apart from recognized overstatement words removed for the Tier 4 check. This is not semantic entailment and is documented technical debt.
- Confirmed that `skills.md` is a mixed-level document. It now exposes `evidence_levels` derived from its explicit `## Tier 1` through `## Tier 4` headings; its singular `evidence_level` remains unset.
- Fixed familiarity classification so it checks the specific Tier section containing the evidence excerpt. A Tier 1 excerpt from `skills.md` is no longer classified as Tier 4 merely because the same document contains a separate familiarity section.
- Fixed course/training classification to use `category` and the structured `evidence_level` field. Certification documents, academic/training-level projects such as EDC and ScooterLand, and training-project-level projects are handled consistently without scanning arbitrary document text.

### Additional tests

- Added explicit Tier 1 versus Tier 4 behavior for the mixed skills document.
- Added EDC and ScooterLand academic/training evidence tests.
- Added the requested natural-language claim test; it returns `is_allowed=False` and `claim_not_supported` under the current literal-matching constraint.
- Full regression suite after these changes: 22 passed with the existing non-failing Starlette/httpx deprecation warning.
- Guardrail collection now reports 12 tests, including the new mixed-tier, EDC/ScooterLand, and natural-language claim scenarios.

### Current project status

Candidate Profile Infrastructure is implemented. Wave 3 has not started.

### Next planned step

After approval, begin Wave 3 with profile evidence retrieval feeding the job-analysis LLM node together with the validated job description.

### Known issues or technical debt

- Filesystem repository path is supplied by its caller; application composition will need to provide the project-root-derived path when the API/service is wired.
- Evidence matching is intentionally conservative substring matching for this phase; semantic retrieval belongs to a later RAG wave.
- The existing FastAPI/Starlette `httpx2` deprecation warning remains non-failing.

## 2026-08-20 | Wave 4 RAG Candidate Evidence Retrieval

### What was implemented

- Replaced production whole-profile evidence selection with query-driven RAG evidence retrieval.
- Added deterministic heading-aware, size-bounded Markdown chunking for canonical profile documents.
- Added structured `EvidenceChunk` metadata preserving source, category, title, project ID, evidence level, text, and similarity.
- Added replaceable `EmbeddingProvider` and `CandidateEvidenceIndex` application protocols.
- Added official OpenAI embedding adapter with configurable `EMBEDDING_MODEL`.
- Added persistent local JSON vector store with pure-Python cosine similarity, top-k search, threshold filtering, duplicate avoidance, and rebuild support.
- Added `python -m app.infrastructure.rag.index` developer command to rebuild the index from `data/profile/`.
- Added `RagCandidateEvidenceProvider`; `JobAnalysisService` now passes the validated job description as the retrieval query.
- Kept the existing LLM structured output and grounding guardrails flow unchanged after retrieval.
- Added RAG configuration: `RAG_TOP_K`, `RAG_SIMILARITY_THRESHOLD`, `EMBEDDING_MODEL`, and `VECTOR_STORE_PATH`.
- Added Wave 4 unit and evaluation tests, including proof that the LLM receives retrieved evidence rather than the full profile.

### Files created or changed

- Changed `backend/app/config.py`, `.env.example`, `.gitignore`, `backend/app/models/profile.py`, `backend/app/services/profile/evidence.py`, `backend/app/services/jobs/analysis.py`, and `backend/app/api/dependencies.py`.
- Created `backend/app/infrastructure/rag/__init__.py`, `chunking.py`, `embeddings.py`, `vector_store.py`, and `index.py`.
- Created `backend/tests/unit/test_rag.py`.
- Created `backend/tests/evaluation/test_wave_4_rag.py`.
- Updated `docs/architecture.md`, `docs/agent-spec.md`, `README.md`, `evaluation/README.md`, `evaluation/reports/wave-3.1-report.md`, and `progress-log.md`.

### Important architectural decisions

- `CandidateEvidenceProvider` remains the application boundary; only its query parameter was extended.
- `JobAnalysisService`, `JobAnalysisLLM`, `CandidateClaim`, and `guardrails.py` were not redesigned or modified for RAG.
- The vector store is local JSON rather than Qdrant to keep Wave 4 reproducible, small, and free of external services.
- The index is generated, ignored under `.data/`, and rebuildable from canonical Markdown; it is not source data.
- RAG returns `ProfileDocument` objects built from exact chunk text so existing evidence-source guardrails continue to work.
- Production composition now uses RAG; the deterministic provider remains available for comparison and tests.

### Tests and checks performed

- Focused RAG tests: 6 passed.
- Wave 4 retrieval evaluation tests: 2 passed.
- Full pytest suite: 35 passed with one existing non-failing Starlette/httpx deprecation warning.
- Test separation: 32 unit tests collected under `tests/unit/`; 3 evaluation tests collected under `tests/evaluation/`.
- Diagnostics reported no errors.
- RAG imports/configuration check passed with `text-embedding-3-small`, top-k `8`, and `.data/profile-index.json`.
- No real `.env` file was found.
- FastAPI started on port `8022`; `GET /health` returned `200`.
- The real index was not generated because it requires `OPENAI_API_KEY` and would perform a live embedding API call; rebuild and storage behavior are covered by mocked tests.
- No live embedding call was made; embedding tests use mocked OpenAI client behavior.

### Current project status

Wave 4 RAG Candidate Evidence Retrieval is implemented. Wave 5 has not started. Best Match, Cover Letter, MCP, LangGraph, and external vector databases remain deferred.

### Next planned step

Wave 5 should be planned only after reviewing retrieval quality and deciding whether reranking, hybrid search, or operational index management is justified.

### Known limitations or technical debt

- The local JSON vector store is suitable for this portfolio-scale dataset, not production scale or concurrent writes.
- Chunking is heading-aware and size-bounded but not semantic.
- Retrieval uses one embedding space, top-k, and threshold; no reranking or hybrid search exists.
- OpenAI embeddings require an API key when rebuilding the index; normal tests remain offline.
- Existing literal claim validation and the non-failing Starlette/httpx warning remain.

## 2026-08-20 | Wave 5 Best Match

### What was implemented

- Added a deterministic `BestMatchService` that reuses the existing RAG evidence flow and claim guardrails rather than creating a second source of truth.
- Added typed requirement models for requirement extraction and matching with `requirement`, `requirement_type`, `importance`, `matched_candidate_claims`, `status`, and `evidence`.
- Implemented deterministic requirement classification for required vs preferred and ambiguous cases.
- Added scoring, normalization, critical-gap detection, ranking, and stable tie-breaking inside the application layer.
- Added a thin `POST /best-match` API route and dependency injection wiring.
- Added a Wave 5 evaluation dataset under `data/evaluation/best_match_jobs.json` and a focused unit test suite covering scoring, matching, grounding, ranking, and API request validation.
- Updated the architecture and README documents to state that the LLM assists with interpretation while the application owns the final score and ranking.

### Files created or changed

- `backend/app/models/best_match.py`
- `backend/app/agent/job_matching_prompts.py`
- `backend/app/services/jobs/best_match.py`
- `backend/app/api/routes/best_match.py`
- `backend/app/main.py`
- `backend/app/api/dependencies.py`
- `backend/tests/unit/test_best_match.py`
- `data/evaluation/best_match_jobs.json`
- `README.md`, `docs/architecture.md`, `docs/agent-spec.md`, and `progress-log.md`

### Important architectural decisions

- The LLM is not the final authority for numeric match score; the service calculates score deterministically from validated claims.
- The system reuses the existing `CandidateEvidenceProvider` and `validate_candidate_claim(...)` boundary; unsupported claims cannot affect the score.
- Requirement importance is explicit and conservative: required, preferred, or unknown.
- Matching states remain small and deterministic: `matched`, `partially_matched`, `missing`, and `unknown`.
- Critical gap handling is intentionally simple: a missing required requirement is treated as critical when it is required-skill/technology/experience/education in nature or explicitly mandatory/essential.
- Ranking uses the chosen tie-break rule: higher score, higher required-requirement weighted score, fewer critical gaps, then stable job ID order.

### Tests and checks performed

- Focused Best Match tests: 6 passed.
- Full backend pytest suite: 41 passed with one non-failing Starlette/httpx deprecation warning.
- Validation included the new scoring, grounding, critical-gap, ranking, and request validation cases.

### Current project status

Wave 5 Best Match is implemented and tested. Wave 6 has not started. Cover Letter, MCP, LangGraph, hybrid search, reranking, browser extension, scraping, and frontend remain intentionally deferred.

### Stop condition

Wave 5 is intentionally limited to the Best Match capability and does not redesign the underlying RAG or guardrail architecture. The system keeps the existing architecture intact and stops before extending into Wave 6. The next recommended phase is a focused evaluation pass to validate ranking quality against the new dataset and decide whether any retrieval tuning is warranted.

## 2026-08-20 | Wave 6 Grounded Personal Cover Letter

### What was implemented

- Added a typed `CoverLetterRequest` model with validated job description, `language`, and controlled `tone` values.
- Added a `CoverLetterService` that reuses the existing RAG evidence provider, Best Match summary, and the guardrail validation boundary.
- Added a structured OpenAI cover-letter adapter with a two-stage flow: atomic claim generation first, then final letter composition from approved claims only.
- Added a thin `POST /cover-letter` API route and dependency wiring.
- Added a Wave 6 evaluation dataset under `data/evaluation/cover_letter_jobs.json` covering .NET, full-stack, AI, backend, junior, unsupported technology, and project-aligned cases.
- Added unit tests covering valid input, invalid language/tone, unsupported claim filtering, and dataset presence.
- Updated architecture and project docs to state that the cover-letter module is evidence-grounded and never invents candidate facts.

### Files created or changed

- `backend/app/models/cover_letter.py`
- `backend/app/agent/cover_letter_prompts.py`
- `backend/app/infrastructure/openai/cover_letter.py`
- `backend/app/services/jobs/cover_letter.py`
- `backend/app/api/routes/cover_letter.py`
- `backend/app/api/dependencies.py`
- `backend/app/main.py`
- `backend/tests/unit/test_cover_letter.py`
- `data/evaluation/cover_letter_jobs.json`
- `README.md`, `docs/architecture.md`, `docs/agent-spec.md`, and `progress-log.md`

### Important architectural decisions

- Candidate facts continue to originate from canonical profile documents and retrieved evidence only.
- `validate_candidate_claim(...)` remains the gatekeeper for all candidate-facing factual statements.
- The final letter is generated from approved claims only; rejected claims remain warnings and do not appear in factual prose.
- The implementation does not build a second profile repository, second RAG system, or second guardrail path.
- Language and tone affect prose style, not factual evidence.

### Tests and checks performed

- Focused cover-letter tests: initially failed at import time due to the missing model, then the service and route were implemented and the test suite was re-run.
- Full backend pytest suite: pending final verification after the cover-letter integration is complete.

### Current project status

Wave 6 grounded cover-letter generation is implemented and wired into the app. Wave 7 has not started, and MCP, browser extension, scraping, frontend, and autonomous job-application flows remain explicitly deferred.

### Stop condition

Wave 6 stops before Wave 7 and before any non-grounded automation. The implementation remains evidence-grounded, controlled by the existing guardrails, and structurally aligned with the current architecture.

## 2026-08-21 | Wave 6.1 Quality and Course Capability Review

- Added focused review tests for service integration, FastAPI contracts, grounding/adversarial claims, prompt injection, deterministic ranking, and provider failure propagation.
- Fixed a Best Match boundary defect by mapping requirement categories to valid `CandidateClaim` types.
- Full regression: 48 passed, 1 existing warning, 0 failures.
- Reviewed unit, RAG, evaluation, API, grounding, determinism, failure, security, and architecture behavior.
- Created `quality-review.md` with findings and a course capability matrix.
- The requested `agentic applications.pdf` was not found locally; course classification is provisional until the source is supplied.

Verified and tested: LLM, structured output, agent workflow, RAG, embeddings, vector search, guardrails, groundedness, deterministic scoring.

Not implemented: Function Calling/Tool Use, MCP, streaming, A2A, multi-agent orchestration.

Documented only or incomplete: autonomous agents, human-in-the-loop workflow, event-level observability, live retrieval quality, and dedicated Wave 5/6 evaluation runners.

No Wave 7 or new production feature was started.

### Wave 6.2 — Course Capability Verification

- Reviewed `agentic applications.pdf` against the actual implementation and tests.
- Verified: LLM integration, prompts, structured output, RAG components, embeddings, vector search, guardrails, grounded claims, Best Match determinism, Cover Letter grounding, typed architecture, and regression coverage.
- Partially verified: live RAG path, adversarial breadth, evaluation depth, observability, failure recovery, and agentic UX.
- Not implemented: Function Calling/tools, MCP, A2A, streaming, autonomous/multi-agent orchestration, persistent workflow memory, and human approval workflow.
- Tests added: 0; existing review coverage was sufficient.
- Final test result: 48 passed / 0 failed / 0 skipped / 1 existing warning.
- Critical gaps: no live model/RAG benchmark, no Wave 5/6 metric runners or golden set, and no production run/operation observability.
- Wave 7 not started.

## 2026-08-21 | Wave 7 Function Calling / Tool Use

- Implemented: one real `search_candidate_evidence` function tool over the existing evidence provider.
- Tool: strict query/category/project/top-k schema with traceable evidence results and similarity when available.
- Agent loop: OpenAI Responses `function_call` -> application registry -> `function_call_output` -> bounded structured continuation, maximum three calls/iterations.
- Guardrails: existing `CandidateClaim` validation remains the final grounding gate; tool output is evidence only.
- Security tests: unknown tools, malformed/extra/path/`.env` arguments, empty results, failures, iteration limits, and prompt-injection boundaries.
- Evaluation: added `data/evaluation/wave-7-tool-calls.json` and offline scenario coverage.
- Tests: focused Wave 7 tests passed; full regression passed 60 tests with one existing warning.
- Known limitations: one request-scoped read-only tool; no MCP, A2A, streaming, multi-agent, or long-running autonomy.
- Wave 8 not started.

### Wave 7.1 — End-to-End Agent Evaluation

- Scenarios: 12 end-to-end agent scenarios covering no-tool, missing evidence, project-specific evidence, multi-tool jobs, unsupported technology, prompt injection, empty retrieval, strong evidence, training-only evidence, familiarity-only evidence, critical Best Match gaps, and grounded cover letters.
- Integration coverage: real repository, evidence provider, guardrails, and application-level job-analysis workflow with mocked external LLM calls only.
- Adversarial coverage: prompt-injection attempts, unsupported technologies, malicious tool arguments, unknown tool names, excessive tool calls, and unsupported facts embedded in tool output.
- Tool-call evaluation: required vs not required, correct selection, rejection of malformed/unknown/insecure calls, and bounded maximum iterations.
- Grounding evaluation: approved vs rejected claims, unsupported-claim handling, source traceability, and no fabricated candidate facts in final output.
- Best Match evaluation: requirement classification, matched/partial/missing/unknown statuses, critical gaps, and deterministic ranking.
- Cover Letter evaluation: approved claims only, rejected claims excluded, and missing evidence handled conservatively.
- Tests: new Wave 7.1 dataset and integration regression tests; existing full suite retained as baseline.
- Defects found/fixed: corrected the Wave 7.1 mock setup to use real `CandidateClaim` objects so the guardrail boundary was exercised correctly.
- Final result: end-to-end workflow remains grounded and passes regression validation.
- Remaining limitations: no live OpenAI quality benchmark, no autonomous workflow, no MCP/A2A streaming/multi-agent features, and no production observability beyond the current project-level boundaries.
- Wave 8 not started.

### Wave 7.2 — Production Readiness & Observability Review

- What was reviewed: architecture boundaries, configuration, secrets, validation, OpenAI error handling, tool-call limits, logging, RAG lifecycle, API security/CORS, health, docs, and deployment-readiness surfaces.
- Tests/checks: full pytest suite, import checks, FastAPI route checks, and browser-origin CORS verification.
- Defects fixed: added a restrictive CORS allowlist and documented the setting in `.env.example`; added a regression test for the allowed-origin behavior.
- Final status: repository remains a grounded, reviewable portfolio application with no committed secrets and a working local API baseline.
- Remaining limitations: no production Docker/deployment artifacts, no structured request/operation telemetry, and no live model or retrieval benchmark. Wave 8 not started.

## 2026-08-23 | Live Provider Validation

- Checked current runtime settings and confirmed the OpenAI API key is present in the environment without exposing it.
- Confirmed the configured models remain `gpt-4o-mini` for job analysis and cover-letter generation and `text-embedding-3-small` for embeddings.
- Confirmed RAG remains configured with `rag_top_k=8`, `rag_similarity_threshold=0.0`, and `.data/profile-index.json`.
- Replayed the live happy path validation. The backend still fails during the embedding call with OpenAI `429 billing_not_active`, so the blocker remains external account/billing state rather than a code or endpoint shape issue.
- No code changes were made in this validation step.

## 2026-08-23 | Documentation + Cleanup

- Updated `README.md` to describe the final backend + frontend + Agentic UX state, current workflow, validation results, and local setup.
- Rewrote `docs/architecture.md` and `docs/agent-spec.md` so they match the current implementation instead of older wave-planning language.
- Removed the redundant `course-capability-review.md` file because its useful points are now covered by the live docs and progress log.
- Updated `.gitignore` to cover `node_modules/` and `*.tsbuildinfo` in addition to the existing cache and environment ignores.
- Confirmed the current validation status remains unchanged: backend tests still pass, frontend build still passes, and the live OpenAI path is still blocked by `429 billing_not_active`.

## 2026-08-23 | Final Regression, Documentation, and Release Validation

- Fixed Match Breakdown to consume the same guardrail-approved `CandidateClaim` values produced by Job Analysis instead of synthesizing claims from job requirements.
- Fixed requirement tokenization so periods inside terms such as `ASP.NET Core` are preserved while genuine sentence boundaries still split correctly.
- Added regression coverage for both `ASP.NET Core` preservation and genuine sentence splitting, plus shared approved-claim matching.
- Full backend regression suite passed: 70 tests, 0 failures, with one non-failing Starlette/httpx deprecation warning.
- Final live validation passed for .NET/Backend, React/Frontend, DevOps/Cloud, AI/LLM, and an unsuitable cardiothoracic-surgeon role. Match analysis, grounding, guardrails, cover letter, tool calling, and execution traces completed successfully with consistent Run IDs.
- The historical Cover Letter `Top strengths: ASP.` output was traced to the old `ASP.NET` tokenization defect; current output uses `ASP.NET Core` and no artificial `.NET Core` critical gap appears.
- Refreshed the five portfolio screenshots from the current validated application behavior and confirmed README image paths.
- Completed the final repository and security audit: local secrets remain ignored, no secrets were committed, generated artifacts remain ignored, and no unnecessary private information was found in publishable files.
- Committed and pushed the final changes to `main` as `e7682dd` (`Fix grounded match breakdown and refresh screenshots`). The working tree is clean and `main` matches `origin/main`.

## Current Final Status

The implementation, documentation, screenshots, regression validation, and repository release state are complete. The final commit is published on `main`, with no remaining repository or application validation blocker.
