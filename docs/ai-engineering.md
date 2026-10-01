# Latent: evidence-first AI

## Product value

The AI layer helps someone understand a portfolio, rather than adding another dashboard or pretending to forecast prices.

- **Review my portfolio:** a short brief with backend figures, plain-language interpretation, and a link to the next relevant page.
- **Ask a question:** local retrieval selects relevant facts. An available provider explains them using a constrained response contract. Evidence and limitations are expandable in the answer.
- **Check my data:** deterministic checks for missing valuations, old analytics, incomplete review inputs, and model availability. This uses no external AI call and is deliberately labeled local, not AI-powered validation.
- **Reports:** server-generated figures remain intact. A provider can append a clearly separated interpretation, but cannot replace the factual report.

No new page, account tier, vector database, autonomous trading agent, or paid embedding service is required.

## Architecture

```text
Authenticated request + portfolio ownership check + durable rate limit
  -> prompt checks and bounded recent user questions
  -> server portfolio analytics
  -> allowlisted evidence projection + mandatory data-quality caveats
  -> local HashingVectorizer ranking / LangChain Documents
  -> bounded LangChain/provider call (optional)
  -> Pydantic JSON contract + retrieved evidence-reference checks
  -> server inserts exact financial values and navigation action
  -> explanation + actual sources + limitations

Provider timeout, unavailable key, or rejected output
  -> labeled deterministic local explanation
```

`src/ai/evidence.py` owns the provider-facing data projection. It excludes account identifiers, portfolio names, descriptions, trade notes, raw CSV files, and free-text risk-profile fields. Known sector labels are allowlisted. It retains selected holding symbols/weights, the stated loss limit, and screened rule-based recommendation evidence so portfolio questions remain useful. Non-finite numbers are omitted, not replaced with zero. Financial facts still contain sensitive investment information: this is data minimization, not anonymization.

`src/ai/retrieval.py` ranks small evidence records locally. Hash embeddings are lexical feature hashing, **not a learned semantic embedding model**. No external embedding tokens are used. Whole evidence records must fit the context budget; a truncated financial fact cannot be cited. Model limitations and available data-quality warnings are mandatory context. Quality caveats can consume the budget; when no usable evidence fits, the response falls back locally rather than inventing data.

`src/ai/copilot_service.py` uses the existing LangChain prompt/model path for OpenAI-compatible providers and existing adapters for Gemini/Claude. It requests provider-independent JSON and checks it locally, avoiding an assumption that every configured provider supports the same native structured-output API. Responses that use Markdown fences or the wrong shape are rejected. Live provider acceptance rates still need measurement.

`src/ai/safety.py` defines `grounded-readonly-v1`. A model supplies prose, retrieved evidence IDs, and a next-action enum. Financial numbers are rendered from backend records. Model-authored prose containing digits is rejected, as are unknown/duplicate evidence IDs, extra schema fields, links, HTML, recognizable credentials, and some unsafe claims. Navigation destinations are server-owned. These checks do **not** establish that the prose logically follows from its evidence. Words can still contradict a number, and spelled-out claims can evade a numeric check.

## Security boundaries

| Boundary | Enforcement | Important limitation |
| --- | --- | --- |
| Other users' portfolios | Ownership before analytics/provider access; report reads are owner scoped | This does not replace a deployed multi-tenant audit |
| Prompt injection | Narrow data projection, explicit instruction/data separation, no model-executable tools, common-pattern input checks | Pattern checks are bypassable; isolation and lack of capabilities are the stronger controls |
| Credential disclosure | Managed key stays server-side; recognizable secrets in questions are rejected; exact request key echoes are rejected | Not a universal secret/PII detector; users must not paste confidential information |
| Browser provider keys | In-memory only; old persisted key removed; key clears on page reload/unmount | In-memory browser values are still exposed to successful same-origin script compromise |
| Model output | Strict schema, retrieved-source checks, bounded prose, backend-rendered numbers | Semantic correctness and model safety are not proven by schema validation |
| Active content | React text-based Markdown rendering; no raw HTML, external media loading, executable code, or model-controlled actions | Continue testing renderer changes for injection |
| Resource consumption | Existing user/guest/network rate limits; question cap; bounded history/context/output; at most two model candidates sharing one provider deadline; SDK retries disabled | These are not a global monetary cap or a cross-worker concurrency queue |
| Telemetry | Outcome/version/timing only in the new AI event; validation errors omit input values; automatic LangSmith tracing disabled for portfolio calls | Hosting/proxy logs and provider retention policies must also be reviewed |

Request history includes only bounded recent user questions. Browser-supplied assistant text is not accepted as evidence. The model has no tool binding for SQL, shell, trading, network fetching, or mutating a portfolio. Analytics/cache/report persistence is still performed by authorized application code, not model-selected commands.

No response cache was added: avoiding accidental cross-user or stale financial answers is more valuable than a premature cache. Retrieval makes zero embedding API calls. Input token counts are explicitly approximate character-based estimates, not provider billing measurements. Endpoint elapsed time includes context preparation; do not present it as model-only latency.

## Evaluation

Verified locally on 29 September 2026: 231 backend tests passed, including 57 AI API/boundary tests; 10 Playwright tests passed. TypeScript, ESLint, and the optimized production build passed. The production preview was inspected at desktop and mobile sizes in both themes with no horizontal overflow or browser warnings. These checks used isolated test data and mocked AI responses, not Neon or paid provider calls.

Offline tests exercise prompt and output boundaries, benign questions, ownership, rate limits, malformed responses, citation validity, non-finite inputs, privacy projection, missing/stale data, provider timeout, and report preservation. They mock provider responses: passing them is **not** a model accuracy or prompt-injection resistance percentage.

Run the focused suite from the repository root using the test virtual environment:

```sh
ENVIRONMENT=test NVIDIA_API_KEY= MIGRATION_DATABASE_URL= \
  venv/bin/python -m pytest tests/test_ai_api.py tests/test_ai_safety.py \
  -q --junitxml=/tmp/latent-ai-evaluation.xml
```

The existing CI backend test step discovers these tests automatically. The Playwright guest journey exercises the portfolio brief, evidence disclosure, local data checks, rejected-request recovery, report generation, and mobile layout. No new external service or secret is necessary to run these tests.

Before public release, add a consented, non-sensitive live-provider evaluation set. Measure answer relevance, incorrect interpretations, evidence selection, schema acceptance/rejection, fallback rate, p50/p95 end-to-end latency, and actual provider usage/cost. Review dangerous-but-schema-valid answers manually. Test each deployed provider/model and repeat after changing prompts, models, or data definitions. Include questions about missing data and whether regime confidence predicts the future.

## Honest portfolio positioning

> Built an evidence-first financial Copilot with local retrieval, LangChain orchestration, constrained generation, backend-owned numerical facts, privacy-conscious context selection, failure recovery, and automated adversarial tests.

Do not claim a trained semantic embedding model, proven forecast accuracy, a fully autonomous agent, zero hallucinations, complete prompt-injection protection, or a security certification. The health score remains an uncalibrated historical review aid. Trained HMM validation, live PostgreSQL/staging verification, live-provider quality evaluation, and infrastructure security remain separate release requirements.

## References

The boundary design follows the distinction between model instructions and application-enforced authority discussed in [OWASP prompt injection](https://genai.owasp.org/llmrisk2023-24/llm01-24-prompt-injection/), [excessive agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/), and [system prompt leakage](https://genai.owasp.org/llmrisk/llm072025-system-prompt-leakage/). Structured responses are locally validated; see [LangChain's structured output reference](https://reference.langchain.com/python/langchain/agents/structured_output).
