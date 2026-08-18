# Lib

Shared frontend logic lives here:

- `api.ts`: low-level fetch client and API error normalization.
- `api/`: feature-specific React Query hooks, query keys, and backend response adapters.
- `queries.ts`: compatibility export surface for pages that consume backend hooks.
- `types.ts`: frontend-facing data contracts.
- `analytics-derive.ts`: derived health score and recommendation logic.
- `format.ts`: display formatting for currency, dates, percentages, and series.
- `auth.tsx`: browser session state backed by backend HttpOnly cookies.
- `storage.ts`: scoped local storage cleanup helpers.
- `portfolio-context.tsx`: selected portfolio state.

Keep page files focused on workflow/UI. Put reusable calculations here.
