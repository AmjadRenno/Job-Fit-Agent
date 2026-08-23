# Wave 3.1 Evaluation Report

Date: 2026-08-20
Dataset version: `wave-3.1`
Scope: Wave 3 Job Analysis grounding and evaluation contract
Mode: Offline structured-output fixtures; no live OpenAI call

## Evaluation Cases

| ID | Job type | Expected focus |
| --- | --- | --- |
| `junior-software-developer` | Junior Software Developer | C#, .NET, REST APIs, testing, Git |
| `backend-developer` | Backend Developer | ASP.NET Core, EF Core, SQL, auth, Clean Architecture |
| `full-stack-developer` | Full-Stack Developer | React, TypeScript, JavaScript, APIs, Docker |
| `dotnet-developer` | .NET Developer | ASP.NET Core, Blazor, EF Core, SQL, security |
| `ai-llm-developer` | AI / LLM Developer | LLM applications, function calling, RAG, evaluation |
| `agentic-ai-engineer` | AI Engineer / Agentic AI | Agentic AI, LangGraph, OpenAI Responses API, guardrails |
| `rag-software-developer` | Software Developer with RAG | RAG, embeddings, vector databases, APIs, testing |
| `cloud-devops-software-developer` | Cloud / DevOps Software Developer | Docker, Compose, GitHub Actions, CI/CD, configuration |

The job descriptions are evaluation inputs only. Candidate facts remain sourced from `data/profile/`.

## Methodology

The evaluation fixture sends each job through the real `JobAnalysisService` with:

1. The real deterministic `CandidateProfileRepository`.
2. The real deterministic `CandidateEvidenceProvider`.
3. A mocked structured LLM output containing supported claims and, in four cases, an intentionally unsupported `Kubernetes` claim.
4. The real `validate_candidate_claim(...)` guardrail.
5. The real final-analysis construction path.

This is a contract and grounding evaluation, not a live model-quality benchmark. It verifies that unsupported fixture claims are rejected and cannot enter final candidate claims.

## Aggregate Metrics

| Metric | Result |
| --- | ---: |
| Cases | 8 |
| Average grounding | 0.75 |
| Average relevance | 1.00 |
| Average unsupported-claim rate | 0.25 |
| Average missing-evidence behavior | 1.00 |
| Average claim validation rate | 0.75 |
| Rejected claims excluded from final results | 8/8 cases |
| Forbidden claims in final results | 0 |

The 0.25 unsupported-claim rate is expected in this adversarial offline fixture: four of eight cases include one unsupported raw claim alongside one supported claim. The final approved claim sets contain no unsupported claims.

## Representative Outputs

### Supported claim

```text
Claim: C#
Source: data/profile/skills.md
Evidence excerpt: C# · .NET / ASP.NET Core · Entity Framework Core
Result: approved
```

### Rejected claim

```text
Claim: Kubernetes
Source: data/profile/skills.md
Evidence excerpt: Docker · Testing (xUnit, NUnit, Moq) · Git / GitHub
Result: rejected as claim_not_supported
Final result: claim text excluded; only a generic grounding warning is retained
```

### Missing evidence

The AI/LLM, Agentic AI, RAG, and Cloud/DevOps cases include requirements such as production AI experience, large-scale search infrastructure, Terraform, or Kubernetes. These are represented in `missing_requirements` rather than converted into candidate claims.

## Observed Weaknesses

- This evaluation uses mocked structured outputs and therefore does not measure live OpenAI extraction quality, instruction following, latency, or cost.
- The evidence provider still passes the complete canonical profile rather than semantically selecting evidence.
- Literal claim validation is conservative and rejects natural-language claims that would require semantic entailment.
- Relevance checks use expected claim themes and are intentionally simple; they are not a ranking benchmark.
- The report does not attempt to solve these weaknesses in Wave 3.1.

## Conclusions

The current Wave 3 boundary correctly enforces the most important grounding behavior under offline fixtures:

- Candidate claims are tied to canonical evidence sources.
- Unsupported claims are rejected by the existing guardrails.
- Rejected claim text does not enter final approved candidate claims.
- Missing requirements remain explicit instead of becoming invented qualifications.
- Evaluation is separate from ordinary unit tests and does not require an API key.

The next architectural improvement should be evaluated rather than assumed: semantic retrieval may reduce irrelevant evidence passed to the model, while semantic entailment or claim decomposition may improve recall without weakening grounding.

## Wave 4 Retrieval Follow-up

The Wave 4 comparison fixture confirms the intended scope change for one representative backend job:

- Wave 3 deterministic selection: 15 document-level evidence objects.
- Wave 4 retrieval fixture: 1 relevant chunk.
- Canonical source traceability: preserved (`data/profile/skills.md`).
- Original evidence excerpt: preserved exactly in the retrieved chunk.

This is an architectural behavior check, not a live embedding-quality score. A broader retrieval-quality evaluation should use a rebuilt index and real embedding calls after credentials and operational cost are available.
