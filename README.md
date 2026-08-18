# Regime Aware Portfolio Risk Analytics

Production-oriented MVP for portfolio persistence, market data ingestion, risk analytics, regime detection, and a Next.js dashboard.

## Stack

- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic settings, pytest.
- Database: SQLite for local development; PostgreSQL recommended for deployment.
- Analytics: pandas, NumPy, scikit-learn, hmmlearn.
- Market data: provider abstraction with Yahoo Finance provider, caching, validation, and database persistence.
- Frontend: Next.js, React, TypeScript, Tailwind CSS, TanStack Query.

## Backend Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Run migrations:

```bash
alembic upgrade head
```

Start the API:

```bash
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Health checks:

- `GET http://127.0.0.1:8000/api/v1/health`
- `GET http://127.0.0.1:8000/api/v1/version`

## Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev -- --hostname localhost --port 3000
```

Open `http://localhost:3000`.

For browser auth cookies, keep hostnames consistent. Use `localhost` for both frontend and API, or `127.0.0.1` for both.

## Environment

Backend configuration lives in `.env`.

Important values:

- `DATABASE_URL`: local SQLite or production PostgreSQL URL.
- `AUTH_SECRET_KEY`: must be a long random secret in production.
- `AUTH_COOKIE_SECURE`: `true` when deployed behind HTTPS.
- `CORS_ORIGINS`: exact frontend origins; do not use wildcard in production.
- `RUN_MIGRATIONS_ON_STARTUP`: optional deployment convenience, usually `false` for controlled releases.
- `MARKET_DATA_PROVIDER`: provider key, currently `yahoo`.
- `MARKET_DATA_REFRESH_ENABLED`: enables scheduled market refresh.
- `FII_DII_CSV_PATH`: local FII/DII flow CSV path.
- `REGIME_MODEL_DIR`: directory for trained regime artifacts.

Frontend configuration lives in `frontend/.env.local`.

Important value:

- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`

## Tests

Backend:

```bash
source venv/bin/activate
pytest
```

Frontend:

```bash
cd frontend
npm run test:production
```

Focused frontend checks:

```bash
npm run typecheck
npm run lint
npm run build
```

## Migrations

Create a new migration after schema changes:

```bash
alembic revision --autogenerate -m "describe schema change"
```

Apply migrations:

```bash
alembic upgrade head
```

Inspect current migration:

```bash
alembic current
```

For real deployment, start from a managed PostgreSQL database and apply Alembic migrations as part of release automation.

## Deployment Assumptions

- Serve the backend over HTTPS.
- Set `AUTH_COOKIE_SECURE=true`.
- Use strong `AUTH_SECRET_KEY`.
- Use PostgreSQL instead of local SQLite.
- Run Alembic migrations before serving new backend code.
- Configure exact production `CORS_ORIGINS`.
- Treat external market APIs as refresh sources, not as a dependency for every user request.
- Keep generated folders ignored: `venv/`, `.pytest_cache/`, `.next/`, `node_modules/`, and build cache files.

## Project Layout

- `src/api/`: FastAPI app, routes, dependencies, schemas, and error handling.
- `src/auth/`: password hashing and JWT helpers.
- `src/database/`: SQLAlchemy engine/session/models.
- `src/portfolio/`: portfolio CRUD, trades, CSV import, positions, returns.
- `src/market/`: market providers, fetching, caching, persistence, feature matrix building.
- `src/analytics/`: risk analytics, regime orchestration, persistence helpers.
- `src/regime/`: HMM prediction, probability, labelling, summaries.
- `scripts/smoke/`: legacy exploratory smoke scripts that may use external market data.
- `frontend/src/app/`: Next.js route entry points.
- `frontend/src/features/`: page-specific product workflows.
- `frontend/src/components/`: reusable UI, layout, chart, and domain components.
- `tests/`: pytest suite using standard `test_*.py` discovery.
