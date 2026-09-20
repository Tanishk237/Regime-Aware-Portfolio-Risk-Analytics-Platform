# Security Policy

## Supported Version

Security fixes are applied to the current `main` branch. Public deployments should run a
reviewed commit, keep dependencies current, and execute the release checks before promotion.

## Reporting A Vulnerability

Do not open a public issue containing credentials, personal data, or an exploitable proof of
concept. Use the repository's private GitHub security advisory flow and include the affected
commit, route or component, reproduction steps, impact, and any suggested remediation.

## Security Properties

- Every portfolio-owned route must resolve the authenticated user and verify ownership.
- Guest credentials and user-supplied AI credentials remain tab-scoped; managed provider
  credentials remain server-side only.
- Production uses PostgreSQL over TLS, HTTPS-only authentication cookies, explicit CORS
  origins, explicit trusted hosts, and a non-default authentication secret.
- Upload limits, schema validation, durable rate limits, request IDs, and structured error
  responses are enforced at the API boundary.
- Deleting an account cascades through its portfolios, analytics, recommendations, alerts,
  stress results, and AI reports. Expired guest records are removed by lifecycle maintenance.
- Market-data fallbacks must identify their source and age. HMM state-fit probability must
  never be presented as predictive accuracy.

## Secret Handling

Keep `.env` files and provider credentials out of Git. Store production values in the hosting
platform's secret manager. The CI secret scan is a final guard, not a replacement for secret
rotation. Any credential pasted into chat, logs, an issue, or a commit must be revoked and
replaced before deployment.

## Release Expectations

Run `./scripts/release-check`, migrate PostgreSQL with `alembic upgrade head`, verify
`/api/v1/ready`, confirm a recent restorable backup, and review dependency/security alerts.
Production model readiness additionally requires a passing leakage-safe regime validation
report when `REQUIRE_VALIDATED_REGIME_MODEL=true`.
