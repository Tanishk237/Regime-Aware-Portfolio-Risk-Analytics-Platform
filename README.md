# Latent

Portfolio Regime Intelligence.

Production-oriented MVP for portfolio persistence, market data ingestion, risk analytics, regime detection, and a Next.js dashboard.

The product lets a user create portfolios, diagnose and import trade CSVs, calculate positions and returns, enrich holdings with market prices, run risk and regime analytics, receive evidence-backed actions, ask grounded portfolio questions, and generate reports.

## Current Capabilities

- JWT-based signup/login plus tab-scoped guest sessions, with protected API routes.
- One-click demo portfolio and a first-run CSV import path for fast onboarding.
- Portfolio CRUD with user-level authorization.
- Manual trade entry, edit, delete, and intelligent CSV preview with column mapping and row-level validation.
- Position calculation with buy/sell support, fees, taxes, realized P&L, unrealized P&L, and market weights.
- Portfolio summary, persisted portfolio returns, and dashboard chart series.
- Market data provider abstraction with Yahoo Finance provider, caching, validation, persistence, retries, and stored-data fallback.
- Historical prices, live prices, India VIX, FII/DII flow ingestion, market index data, and feature matrix generation.
- Risk analytics: returns, P&L, CAGR, drawdown, rolling volatility, VaR, CVaR, Sharpe, Sortino, Calmar, and annualized volatility.
- Regime analytics: versioned HMM artifacts, runtime HMM training, deterministic emergency fallback, regime probability, history, transition matrix, statistics, durations, and state labels.
- Portfolio intelligence context shared by the dashboard, metric explanations, recommendation center, alerts, stress tests, reports, and Copilot.
- Persisted instrument metadata and interactive sector allocation, with sector concentration evidence shared by the dashboard, recommendations, and Copilot.
- Personalized risk profiles that tune recommendation thresholds without changing measured analytics.
- Natural-language stress scenario interpretation with explicit user confirmation, position attribution, and persisted results.
- Optional OpenAI, Gemini, or Claude generation using a user-supplied tab-scoped key, server-managed NVIDIA generation, and a clearly labeled local grounded mode.
- Next.js frontend with responsive dark/light themes, an explained decision dashboard, portfolio, trades, upload, market data, risk, regime, stress test, health, recommendations, settings, and AI Copilot screens.
- Playwright coverage for the complete guest-to-analytics journey using the repository sample CSV.

## Stack

- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic settings, pytest.
- Database: PostgreSQL by default for local, CI, and production operation. SQLite remains an
  isolated automated-test and one-time migration source only.
- Analytics: pandas, NumPy, scikit-learn, hmmlearn.
- AI orchestration: LangChain Core and LangChain OpenAI for OpenAI-compatible chat models, with local zero-token context retrieval.
- Market data: provider interface plus Yahoo Finance implementation.
- Frontend: Next.js, React, TypeScript, Tailwind CSS, TanStack Query, Recharts.

## Project Layout

```text
.
├── alembic/                 # Database migrations
├── data/                    # Local data files and SQLite database
├── frontend/                # Next.js frontend application
├── models/                  # Optional trained HMM artifacts
├── scripts/                 # Utility scripts
├── src/
│   ├── analytics/           # Risk and regime orchestration
│   ├── api/                 # FastAPI app, routes, schemas, dependencies, errors
│   ├── auth/                # Password hashing and JWT helpers
│   ├── database/            # SQLAlchemy models, engine, sessions
│   ├── features/            # Portfolio, market, and flow feature builders
│   ├── ingestion/           # Market/FII-DII/VIX ingestion helpers
│   ├── intelligence/        # Context, profiles, explanations, actions, stress, reports
│   ├── market/              # Provider abstraction, cache, persistence, feature service
│   ├── portfolio/           # Portfolios, trades, CSV upload, positions, returns
│   ├── regime/              # HMM prediction, probabilities, labelling, summaries
│   └── risk/                # Lower-level risk calculations
├── testing/                 # Manual test fixtures, including sample CSV upload
└── tests/                   # Pytest suite
```

Frontend layout:

```text
frontend/src/
├── app/                     # Next.js route entry points
├── components/              # Shared UI, layout, chart, and finance components
├── features/                # Page-specific product modules
└── lib/                     # API client, adapters, auth, formatting, query hooks
```

## Prerequisites

- Python 3.12 recommended.
- Node.js 20+ recommended.
- npm.
- Docker Desktop for the shortest local PostgreSQL setup, or PostgreSQL 15+ installed directly.
- Internet access for live market refreshes through Yahoo Finance.

The application is PostgreSQL-first. SQLite is intentionally limited to isolated tests and
the supplied transfer utility.

## Quick Start

Start backend and frontend together from the repository root:

```bash
./scripts/dev
```

On first run, this starts the `db` service from `compose.yaml`, waits for PostgreSQL, and
applies all Alembic migrations before starting the API and frontend.

Frontend opens at `http://localhost:3000/login`.
Backend health is at `http://127.0.0.1:8000/api/v1/health`.

## Backend Setup

From the repository root:

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Latent AI uses the server-managed NVIDIA provider by default. Create a fresh NVIDIA API
Catalog key and set it only in the backend `.env`:

```env
NVIDIA_API_KEY=replace-with-a-new-key
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
NVIDIA_FALLBACK_MODELS=z-ai/glm-5.3-flash,z-ai/glm-5.3
```

Never prefix the key with `NEXT_PUBLIC_`, commit it, place it in `frontend/.env.local`,
or paste it into the browser. Restart the backend after changing `.env`. The backend owns
the managed model choice and retries the configured fallback models only when the provider
reports that a model is unsupported or unavailable.

Start PostgreSQL and apply migrations:

```bash
./scripts/bootstrap
```

Start the API:

```bash
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Health checks:

```bash
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/ready
curl http://127.0.0.1:8000/api/v1/version
```

`/health` only proves the process is alive. `/ready` additionally proves database
connectivity, schema revision, and the optional model-validation release gate.

Interactive API docs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Frontend Setup

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev -- --hostname localhost --port 3000
```

Open:

```text
http://localhost:3000
```

Important: keep browser/API hostnames consistent for auth cookies. Prefer:

- Frontend: `http://localhost:3000`
- API base URL: `http://localhost:8000/api/v1`

If you use `127.0.0.1` for one service and `localhost` for the other, browser cookies can look missing.

## Environment Variables

Backend configuration lives in `.env`.

Common local values:

```env
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg://latent:latent@localhost:5432/latent
DATABASE_SSL_MODE=disable
RUN_MIGRATIONS_ON_STARTUP=false
AUTH_SECRET_KEY=replace-with-a-long-random-secret
AUTH_COOKIE_SECURE=false
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
MARKET_DATA_PROVIDER=yahoo
MARKET_DATA_CACHE_TTL_SECONDS=900
INSTRUMENT_METADATA_TTL_DAYS=30
INTELLIGENCE_CACHE_TTL_SECONDS=60
GZIP_MINIMUM_SIZE_BYTES=1000
SLOW_REQUEST_THRESHOLD_MS=1500
FII_DII_CSV_PATH=data/external/fii_dii.csv
REGIME_MODEL_DIR=models
```

Important backend settings:

- `DATABASE_URL`: PostgreSQL connection URL. SQLite is supported only for tests and transfer.
- `DATABASE_SSL_MODE`: `disable` for the local container; production requires `verify-full`
  so both encryption and server identity are verified.
- `AUTH_SECRET_KEY`: long random secret; required to be changed in production.
- `AUTH_COOKIE_SECURE`: set to `true` behind HTTPS.
- `AUTH_COOKIE_SAMESITE`: usually `lax`; use carefully if deploying cross-site.
- `CORS_ORIGINS`: comma-separated allowed frontend origins.
- `RUN_MIGRATIONS_ON_STARTUP`: useful in simple dev flows; controlled release pipelines should run Alembic explicitly.
- `MARKET_DATA_REFRESH_ENABLED`: enables scheduled market refresh.
- `MARKET_DATA_REFRESH_SYMBOLS`: comma-separated symbols for scheduled refresh.
- `INSTRUMENT_METADATA_TTL_DAYS`: refresh interval for persisted company, sector, and industry classifications.
- `INTELLIGENCE_CACHE_TTL_SECONDS`: short-lived risk/regime reuse window; writes and explicit refreshes invalidate it immediately.
- `GZIP_MINIMUM_SIZE_BYTES`: response size at which API compression begins.
- `SLOW_REQUEST_THRESHOLD_MS`: logs completed API requests slower than this threshold.
- `FII_DII_CSV_PATH`: path to the FII/DII flow CSV file.
- `REGIME_MODEL_DIR`: directory where trained HMM artifacts live.

Frontend configuration lives in `frontend/.env.local`.

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_API_TIMEOUT_MS=60000
NEXT_PUBLIC_APP_ENV=development
```

## Database And Migrations

Run migrations:

```bash
source venv/bin/activate
alembic upgrade head
```

Check current migration:

```bash
alembic current
```

Create a migration after model/schema changes:

```bash
alembic revision --autogenerate -m "describe schema change"
```

Apply production migrations before starting the new backend version.

Production database example:

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/regime
DATABASE_SSL_MODE=verify-full
REGIME_RUNTIME_FIT_ENABLED=false
```

### Transfer Existing SQLite Data

The transfer refuses a populated target rather than merging ambiguous records:

```bash
source venv/bin/activate
python scripts/migrate_sqlite_to_postgres.py \
  --source sqlite:///./data/regime.db \
  --target postgresql+psycopg://latent:latent@localhost:5432/latent \
  --dry-run
python scripts/migrate_sqlite_to_postgres.py \
  --source sqlite:///./data/regime.db \
  --target postgresql+psycopg://latent:latent@localhost:5432/latent
```

Take a source backup first and compare table counts after transfer. Keep the SQLite file
read-only until the PostgreSQL deployment has passed the end-to-end journey.

## Manual End-To-End Test Flow

1. Start the backend.
2. Start the frontend.
3. Open `http://localhost:3000`.
4. Sign up or log in.
5. Create a portfolio, try the seeded demo, or upload the sample CSV:

```text
testing/sample_portfolio_trades.csv
```

6. Visit Dashboard and confirm:
   - invested value
   - current value
   - total return
   - cumulative returns chart
   - drawdown chart
   - sector allocation
   - top positions
7. Visit Risk Analytics and run/retry analytics.
8. Visit Regime Analytics and inspect the state drivers, duration, and probability caveat.
9. Open an "Explain this metric" control and verify the value, interpretation, source, and data date.
10. Visit Stress Tests, describe a scenario, review its parsed assumptions, confirm it, and run it.
11. Visit Recommendations to inspect evidence, expected impact, confidence, and active alerts.
12. Visit Settings to record the risk preferences used by recommendations.
13. Visit AI Copilot and run a suggested prompt. It works in labeled local grounded mode without a provider key.
14. Generate a saved report and verify its provider/local mode in report history.

## AI Copilot Architecture

Copilot follows a bounded retrieval-and-generation path:

1. Authenticated backend tools calculate portfolio, risk, regime, position, and recommendation facts.
2. A local `HashingVectorizer` embeds the query and controlled context blocks in process. It does not call an embedding API, retain a vector database, or consume embedding tokens.
3. The retriever always includes the regime-model disclosure, ranks the remaining blocks by cosine similarity, and selects at most `AI_RETRIEVAL_TOP_K` blocks within `AI_RETRIEVAL_CHARACTER_BUDGET`.
4. Long time series are represented by their row count plus first and latest observations rather than inserted in full.
5. LangChain sends the compact prompt and limited recent history to the selected chat model. NVIDIA calls use the OpenAI-compatible NVIDIA API Catalog endpoint and a server-only key.
6. If the provider fails, Latent returns a labeled deterministic explanation built from the same backend facts.

Defaults cap retrieved context at 6,000 characters, conversation history at six messages,
and generated output at 700 tokens. Provider responses expose retrieval counts and an
estimated input-token count for observability, but never expose credentials.

## Regime Model Validation

The HMM posterior probability is a state-fit probability, not forecast accuracy. Latent
therefore reports predictive accuracy as **not evaluated** until a leakage-safe validation
run has been completed. A production validation program should:

1. Define independent labels before evaluation, for example from forward benchmark return,
   realized volatility, and drawdown thresholds reviewed by a domain owner.
2. Use expanding-window walk-forward folds. Fit the scaler, HMM, and state-to-label mapping
   only on data available before each test block.
3. Predict the next untouched block and never use test-period statistics to name hidden states.
4. Aggregate out-of-sample confusion matrices, balanced accuracy, macro F1, per-state
   precision/recall, multiclass Brier score, log loss, and probability calibration.
5. Compare against persistence (tomorrow equals today), majority-state, and simple
   volatility-threshold baselines. The HMM should not be promoted unless it improves on them.
6. Record fold dates, feature/data versions, model seed, label-policy version, and market-data
   timestamps. Report confidence intervals and performance by market period.
7. Monitor feature drift, state occupancy, transition stability, and calibration after release;
   retrain or disable the model when agreed thresholds fail.

Until that process produces a versioned report, a displayed `100%` means that the latest
observed feature row is assigned completely to one inferred state by the fitted model. It does
not mean the next market move has a 100% probability or that the model is 100% accurate.

## Testing

Run the full backend suite:

```bash
source venv/bin/activate
pytest
```

Run focused backend suites:

```bash
pytest tests/test_portfolio_api.py
pytest tests/test_analytics_api.py
pytest tests/test_market_api.py
pytest tests/test_authorization_api.py
pytest tests/test_ai_api.py
pytest tests/test_intelligence_api.py
```

Frontend checks:

```bash
cd frontend
npm run smoke
npm run typecheck
npm run lint
npm run build
```

Full frontend production check:

```bash
npm run test:production
```

Install Chromium once and run the full browser journey:

```bash
cd frontend
npx playwright install chromium
npm run test:e2e
```

The E2E suite starts isolated services on ports `3010` and `8010`, migrates a fresh temporary SQLite database, and uses the offline `test-fixture` market provider. It imports `testing/sample_portfolio_trades.csv` and covers dashboard metrics, explanations, risk, regime evidence, interpreted stress tests, health, recommendation evidence, alerts, grounded Copilot output, saved reports, risk preferences, route protection, and dark/light mobile behavior. The fixture provider is rejected when `ENVIRONMENT=production`.

## Intelligence And AI

Latent keeps calculation and language generation separate:

```text
authenticated user + owned portfolio
    -> portfolio summary, positions, risk, regime, and risk profile
    -> server-owned intelligence context
    -> explanations, recommendations, alerts, stress, and reports
    -> optional LLM wording through controlled context tools
```

- The browser cannot submit arbitrary portfolio facts to Copilot; the backend rebuilds context for the authenticated owner.
- Copilot selects controlled summary, risk, regime, positions, and profile tools from the question.
- Every response identifies its mode as `provider`, `local`, or `local_fallback`, and includes backend citations and a data date.
- User-supplied provider keys live in browser `sessionStorage`, are sent only for the selected request, and are never written to the Latent database.
- Local mode is deterministic, grounded narrative generation. It is useful without an API key but is not presented as external LLM reasoning.
- Recommendations include measurable evidence, a review action, expected effect, confidence, and read state.
- Alerts are surfaced in the application header and recommendation center. They are refreshed from the current portfolio context rather than generated by an ungrounded model.

Primary intelligence routes:

```text
GET  /api/v1/intelligence/portfolio/{portfolio_id}
GET  /api/v1/intelligence/portfolio/{portfolio_id}/explanations/{metric}
GET  /api/v1/intelligence/portfolio/{portfolio_id}/recommendations
GET  /api/v1/intelligence/portfolio/{portfolio_id}/alerts
POST /api/v1/intelligence/portfolio/{portfolio_id}/stress/parse
POST /api/v1/intelligence/portfolio/{portfolio_id}/stress/run
GET  /api/v1/intelligence/profile
PUT  /api/v1/intelligence/profile
POST /api/v1/ai/copilot/chat
POST /api/v1/ai/reports
```

## Market Data Behavior

The intended production flow is:

```text
MarketDataService
    -> cache
    -> database
    -> provider refresh only when needed
    -> analytics
```

External APIs are treated as refresh sources, not as a hard dependency for every dashboard request.

Current behavior:

- Historical prices are stored in `market_prices`.
- Only missing leading or trailing price ranges are fetched and persisted when possible.
- Live prices fall back to latest stored close if the provider fails.
- Every latest-price response identifies its provider or stored source, observation date, and
  stale status; the frontend does not label a stored close as live.
- Company, sector, and industry metadata is stored in `instrument_metadata`, refreshed on a configurable interval, and falls back without blocking analytics.
- Market responses use a shared, bounded in-process cache; the database remains the durable source.
- Feature generation uses portfolio prices first.
- India VIX and FII/DII flows enrich regime features when available.
- If VIX/FII-DII are unavailable, regime analytics can still run from price-derived features.

## Regime Analytics

Regime analytics uses a Hidden Markov Model flow. Compatible versioned artifacts in `REGIME_MODEL_DIR` are preferred; otherwise the service trains a Gaussian HMM from the validated feature matrix for that analysis window.

High-level flow:

```text
portfolio trades
    -> positions and weights
    -> historical market prices
    -> portfolio returns
    -> volatility/drawdown/market/flow features
    -> HMM prediction
    -> regime label, probability, history, transition matrix
```

Legacy or incompatible artifacts are rejected before unpickling. If runtime HMM training also cannot produce a valid result, the API uses deterministic state labelling as an explicit emergency fallback. The response metadata includes:

- `model_name`
- `model_fallback_used`
- `fallback_used`
- `warnings`

That lets the frontend show a useful result while still being honest about degraded data/model quality.

## Performance And Freshness

- Expensive risk and regime payloads are reused for a short configured interval.
- Cache entries include a portfolio revision and are invalidated immediately after portfolio or trade changes.
- Explicit workspace refresh bypasses the intelligence cache.
- Trade changes clear dependent return, risk, regime, recommendation, and alert snapshots before rebuilding.
- Persisted returns are recalculated from the current local price matrix, so new price rows cannot leave risk metrics permanently stale.
- Header alerts are lightweight persisted reads and never train or run the HMM just to render the bell.
- Large API responses are gzip-compressed and successful responses expose `Server-Timing` for diagnosis.
- Frontend requests have a configurable timeout and do not retry deterministic client errors.

## Production Deployment Checklist

- Copy `.env.production.example` into the deployment platform's secret/environment settings;
  never upload the file with real values.
- Use managed PostgreSQL with TLS, automated backups, and point-in-time recovery where offered.
- Set `ENVIRONMENT=production`.
- Set a strong `AUTH_SECRET_KEY` with at least 32 characters.
- Set `AUTH_COOKIE_SECURE=true`.
- Serve backend and frontend over HTTPS.
- Set exact `CORS_ORIGINS` and `TRUSTED_HOSTS`; do not use `*`.
- Run `alembic upgrade head` as a one-off release job before replacing API instances.
- Require `/api/v1/ready` to pass before routing traffic.
- Configure market data refresh jobs if live/stale data matters.
- Configure Sentry or an equivalent error monitor and retain structured request logs by request ID.
- Confirm provider-side AI spend caps in addition to Latent's per-user API rate limit.
- Run and periodically restore-test PostgreSQL backups.
- Store secrets in a secret manager or deployment platform environment settings.
- Run `./scripts/release-check` before release.
- Keep `REQUIRE_VALIDATED_REGIME_MODEL=true` for predictive claims; readiness remains blocked
  until a real leakage-safe report has `validated: true`.
- Keep generated folders untracked: `venv/`, `.pytest_cache/`, `.next/`, `node_modules/`, and build cache files.
- Never configure `MARKET_DATA_PROVIDER=test-fixture` outside automated tests.

### Container Deployment

For a complete local production-shaped stack:

```bash
docker compose up --build
```

For a hosted deployment, build `Dockerfile` as the API service and `frontend/Dockerfile` as
the web service. Point both at their public HTTPS origins, attach the API to managed
PostgreSQL, run the migration job, then health-check `/api/v1/ready`. The frontend build-time
`NEXT_PUBLIC_API_BASE_URL` must be the public API URL; it is not a secret.

Do not rely on `RUN_MIGRATIONS_ON_STARTUP=true` when multiple API replicas can start at once.
It is enabled in local Compose for convenience; production should use one explicit migration
job and leave it `false` on web replicas.

### Staging With Managed PostgreSQL

Staging uses the same hardened settings as production and a dedicated managed PostgreSQL
database. It does not share a database, cookie name, or secret with local development or
production.

Neon connection strings use `sslmode=require&channel_binding=require`. Latent accepts this
combination as a secure deployment transport while continuing to support `verify-full` for
providers configured with a trusted root certificate.

Use Neon's pooled hostname for `DATABASE_URL` and its direct hostname for
`MIGRATION_DATABASE_URL`. API requests benefit from the pooler, while schema migrations run
over a stable direct session. Other PostgreSQL providers may leave `MIGRATION_DATABASE_URL`
blank to reuse `DATABASE_URL`.

1. Provision an empty PostgreSQL database with TLS and point a staging DNS name at the host
   or reverse proxy that will run the containers.
2. Create the private staging configuration:

```bash
cp .env.staging.example .env.staging
openssl rand -hex 32
```

3. Replace the database URL, generated auth secret, frontend/API origins, trusted hosts,
   and optional provider credentials in `.env.staging`.
4. Put HTTPS in front of ports 3000 and 8000. The staging Compose file binds both ports to
   loopback so they are not exposed directly to the internet.
5. Deploy from the repository root:

```bash
./scripts/deploy-staging
```

The deploy command rejects placeholder settings, validates Compose, builds both images,
runs `alembic upgrade head` as a one-off job, starts API and web, and waits for
`/api/v1/ready`. A failed migration or readiness check fails the deployment instead of
silently serving an incompatible schema.

Useful staging operations:

```bash
docker compose --env-file .env.staging -f compose.staging.yaml ps
docker compose --env-file .env.staging -f compose.staging.yaml logs -f api web
docker compose --env-file .env.staging -f compose.staging.yaml down
```

### Backup And Recovery

Create a private custom-format backup:

```bash
export PGSERVICE=latent
export PGSSLMODE=verify-full
./scripts/backup-postgres
```

Restore only into a prepared recovery target:

```bash
export PGSERVICE=latent-recovery
export PGSSLMODE=verify-full
CONFIRM_RESTORE=RESTORE ./scripts/restore-postgres \
  "$HOME/.local/share/latent/backups/latent-YYYYMMDDTHHMMSSZ.dump"
alembic upgrade head
```

`PGSERVICE` should reference a service definition whose password is supplied through a
mode-`0600` `PGPASSFILE` (or another PostgreSQL-supported secret mechanism). This keeps
credentials out of process arguments and shell history. Without a service definition, set
`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, and `PGPASSFILE` explicitly.

Keep backups encrypted, access-controlled, retention-limited, and separate from the primary
database. A backup is not trusted until a restore drill has succeeded.

## Useful Commands

Backend:

```bash
source venv/bin/activate
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
pytest
alembic upgrade head
```

Frontend:

```bash
cd frontend
npm run dev -- --hostname localhost --port 3000
npm run typecheck
npm run lint
npm run build
```

Git status:

```bash
git status --short
```

## Troubleshooting

If `yfinance` repeatedly prints `NotOpenSSLWarning`, the virtual environment was created with a Python build linked to Apple LibreSSL. It is a local TLS compatibility warning from urllib3, not a Latent authentication or analytics error. Recreate the environment with Python 3.12 from Homebrew or another OpenSSL-backed distribution:

```bash
brew install python@3.12
python3.12 -m venv venv312
source venv312/bin/activate
pip install -r requirements.txt
```

Use the new environment for Alembic, pytest, and Uvicorn. Do not suppress the warning in application code because that can hide a real TLS compatibility problem.

## Current Limitations

- OpenAI, Gemini, and Claude keys remain tab-scoped user inputs. NVIDIA uses a server-only environment key. Latent enforces durable per-user AI request limits, but provider-side monetary budgets must still be configured with the provider.
- HMM predictive accuracy is not yet measured because the project does not include independently labeled regimes or a versioned walk-forward report. Posterior state probability must not be presented as forecast accuracy.
- Runtime HMM training is suitable for the MVP; a mature deployment should add an offline training registry, walk-forward evaluation gates, drift monitoring, and signed model artifacts.
- Yahoo Finance is the implemented market provider and has no formal availability SLA; production should add a second provider behind the existing interface.
- Stress tests are sensitivity estimates rather than forecasts. Recommendations are explainable policy rules personalized by the risk profile, not individualized investment advice.
- Alerts are refreshed when portfolio intelligence is generated and read cheaply elsewhere. Time-based push notifications and email delivery require a durable worker and notification provider in a later deployment phase.
- Transactional email is not configured, so email verification and password-reset delivery require an external email provider before offering self-service account recovery.
