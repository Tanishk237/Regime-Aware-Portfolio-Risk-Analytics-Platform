# Regime Aware Portfolio Risk Analytics Frontend

Production Next.js frontend for the Regime Aware Portfolio Risk Analytics Platform.

## Stack

- Next.js App Router
- React 19
- TypeScript
- Tailwind CSS 4
- shadcn/ui primitives
- TanStack React Query
- Recharts
- lucide-react

## Structure

```text
src/
  app/                  Next.js routes and page-level workflows
  components/
    charts/             Chart and section surfaces
    common/             Tables, metrics, states, dialogs, markdown
    domain/             Finance-specific display components
    layout/             App shell, sidebar, topbar, route guards, providers
    motion/             Optional animation helpers
    ui/                 shadcn/ui primitives
  hooks/                Shared React hooks
  lib/                  API client, query hooks, domain derivations, formatting
  styles.css            Design tokens and global utilities
```

## Environment

Copy `.env.example` and set the backend URL:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_ENV=development
```

## Commands

```bash
npm install
npm run dev
npm run test:production
```

Useful checks:

```bash
npm run smoke
npm run typecheck
npm run lint
npm run build
npm audit --omit=dev
```

## Product Notes

- Auth uses backend `/auth/signup`, `/auth/login`, and `/auth/me` endpoints.
- Browser sessions use backend-set HttpOnly cookies; API clients can still use bearer tokens from auth responses.
- API calls are centralized in `src/lib/api.ts`.
- Backend response normalization is handled in focused modules under `src/lib/api/`.
- AI Copilot generates grounded explanations and reports from portfolio, risk, and regime context; provider-key UI is ready for backend AI orchestration.
- Production build uses `next build --webpack` to avoid Turbopack worker port restrictions in local/sandboxed environments.
