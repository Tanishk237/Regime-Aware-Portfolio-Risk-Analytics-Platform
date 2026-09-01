# Regime Aware Portfolio Risk Analytics

Production-oriented MVP for portfolio persistence, market data ingestion, risk analytics, regime detection, and a Next.js dashboard.

The product lets a user create portfolios, add trades manually or by CSV, calculate positions and returns, enrich holdings with market prices, run risk analytics, detect market regimes, view dashboard charts, and inspect portfolio health/recommendations.

## Current Capabilities

- JWT-based signup/login with protected API routes.
- Portfolio CRUD with user-level authorization.
- Manual trade entry, edit, delete, and CSV upload.
- Position calculation with buy/sell support, fees, taxes, realized P&L, unrealized P&L, and market weights.
- Portfolio summary, persisted portfolio returns, and dashboard chart series.
- Market data provider abstraction with Yahoo Finance provider, caching, validation, persistence, retries, and stored-data fallback.
- Historical prices, live prices, India VIX, FII/DII flow ingestion, market index data, and feature matrix generation.
- Risk analytics: returns, P&L, CAGR, drawdown, rolling volatility, VaR, CVaR, Sharpe, Sortino, Calmar, and annualized volatility.
- Regime analytics: HMM-first prediction with deterministic fallback, regime probability, history, transition matrix, statistics, durations, and state labels.
- Next.js frontend with dashboard, portfolio, trades, upload, market data, risk, regime, stress test, health, recommendations, settings, and AI copilot screens.

## Stack

- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic settings, pytest.
- Database: SQLite for local development; PostgreSQL recommended for production.
- Analytics: pandas, NumPy, scikit-learn, hmmlearn.
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

- Python 3.10+ recommended.
- Node.js 20+ recommended.
- npm.
- PostgreSQL for production-like deployment.
- Internet access for live market refreshes through Yahoo Finance.

Local development can run with SQLite.

## Backend Setup

From the repository root:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Apply migrations:

```bash
alembic upgrade head
```

Start the API:

```bash
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Health checks:

```bash
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/version
```

Interactive API docs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Frontend Setup

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev -- --webpack --hostname localhost --port 3000
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
DATABASE_URL=sqlite:///./data/regime.db
RUN_MIGRATIONS_ON_STARTUP=false
AUTH_SECRET_KEY=replace-with-a-long-random-secret
AUTH_COOKIE_SECURE=false
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
MARKET_DATA_PROVIDER=yahoo
MARKET_DATA_CACHE_TTL_SECONDS=900
FII_DII_CSV_PATH=data/external/fii_dii.csv
REGIME_MODEL_DIR=models
```

Important backend settings:

- `DATABASE_URL`: SQLite locally or PostgreSQL in production.
- `AUTH_SECRET_KEY`: long random secret; required to be changed in production.
- `AUTH_COOKIE_SECURE`: set to `true` behind HTTPS.
- `AUTH_COOKIE_SAMESITE`: usually `lax`; use carefully if deploying cross-site.
- `CORS_ORIGINS`: comma-separated allowed frontend origins.
- `RUN_MIGRATIONS_ON_STARTUP`: useful in simple dev flows; controlled release pipelines should run Alembic explicitly.
- `MARKET_DATA_REFRESH_ENABLED`: enables scheduled market refresh.
- `MARKET_DATA_REFRESH_SYMBOLS`: comma-separated symbols for scheduled refresh.
- `FII_DII_CSV_PATH`: path to the FII/DII flow CSV file.
- `REGIME_MODEL_DIR`: directory where trained HMM artifacts live.

Frontend configuration lives in `frontend/.env.local`.

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
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
```

## Manual End-To-End Test Flow

1. Start the backend.
2. Start the frontend.
3. Open `http://localhost:3000`.
4. Sign up or log in.
5. Create a portfolio, or upload the sample CSV:

```text
testing/sample_portfolio_trades.csv
```

6. Visit Dashboard and confirm:
   - invested value
   - current value
   - total return
   - cumulative returns chart
   - drawdown chart
   - top positions
7. Visit Risk Analytics and run/retry analytics.
8. Visit Regime Analytics and run/retry detection.
9. Visit Market Data to verify historical/live market data behavior.
10. Visit AI Copilot to validate the current UI flow.

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

Known local note: in the current workspace, `tsc` and `next build` have occasionally hung silently under the local Next/TypeScript toolchain. Backend tests and Prettier checks pass. Treat frontend build/typecheck stability as a separate release-blocking check before deployment.

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
- Missing price ranges are fetched and persisted when possible.
- Live prices fall back to latest stored close if the provider fails.
- Feature generation uses portfolio prices first.
- India VIX and FII/DII flows enrich regime features when available.
- If VIX/FII-DII are unavailable, regime analytics can still run from price-derived features.

## Regime Analytics

Regime analytics uses a Hidden Markov Model flow when trained artifacts are available in `REGIME_MODEL_DIR`.

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

If HMM artifacts are missing or incompatible, the API falls back to deterministic state labelling. The response metadata includes:

- `model_name`
- `model_fallback_used`
- `fallback_used`
- `warnings`

That lets the frontend show a useful result while still being honest about degraded data/model quality.

## Production Deployment Checklist

- Use PostgreSQL, not local SQLite.
- Set `ENVIRONMENT=production`.
- Set a strong `AUTH_SECRET_KEY` with at least 32 characters.
- Set `AUTH_COOKIE_SECURE=true`.
- Serve backend and frontend over HTTPS.
- Set exact `CORS_ORIGINS`; do not use `*`.
- Run `alembic upgrade head` during release.
- Configure market data refresh jobs if live/stale data matters.
- Persist and back up the database.
- Store secrets in a secret manager or deployment platform environment settings.
- Run backend tests, frontend typecheck, lint, and production build before release.
- Keep generated folders untracked: `venv/`, `.pytest_cache/`, `.next/`, `node_modules/`, and build cache files.

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
npm run dev -- --webpack --hostname localhost --port 3000
npm run typecheck
npm run lint
npm run build
```

Git status:

```bash
git status --short
```

## Current Limitations

- AI Copilot supports provider-backed chat/report generation through a backend proxy using a user-supplied key. Provider keys are not stored on the backend.
- HMM training lifecycle can be improved with explicit training commands, model versioning, and model quality checks.
- Market data currently has Yahoo as the implemented provider; additional providers can be added behind the existing provider interface.
- Stress testing and recommendations are MVP-level and should be deepened with scenario persistence and richer rules.
- Frontend production build/typecheck hang should be debugged before public deployment.
