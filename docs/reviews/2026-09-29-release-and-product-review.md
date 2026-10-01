# Latent: Release, Product Journey, and Health Score Review

Reviewed on 29 September 2026. This is a review, not a production certification or a claim of predictive accuracy. No application behavior was changed during this review.

## Verdict

Latent has a working demonstration journey, useful explanations, and meaningful automated coverage. It is not yet ready to present its portfolio-health number as a validated assessment or its historical chart as the investor's actual performance. Reliability during missing-data and deployment failures is the highest-priority engineering work. More visual features are not the next priority.

For an associate product manager portfolio, the strongest next improvement is a trustworthy, understandable first result: what the user owns, what changed, what needs attention, and how complete the evidence is.

## Scope and Evidence

- Read deployment configuration, authentication/session handling, CSV import, portfolio accounting, risk/regime services, health derivation, recommendations, AI, and the main frontend routes.
- Latest public GitHub CI run remains failed on commit `92d31a1`: [CI run 36340217862](https://github.com/Tanishk237/Regime-Aware-Portfolio-Risk-Analytics-Platform/actions/runs/36340217862). The existing local CI fixes remain uncommitted. CodeQL success is a separate check and does not replace CI success.
- Full backend suite: **155 passed**, with 178 warnings. A first run with a SQLite environment override caused one production-settings test to fail because it checked the database guard before the intended provider guard. With the PostgreSQL-shaped CI environment, all tests passed. This also exposes an environment-isolation weakness in that test.
- Most API tests use their own temporary databases; this result does not mean every feature was integration-tested against Neon or PostgreSQL concurrency.
- Production frontend build and lint passed in an isolated clean frontend copy. The copy used the committed frontend plus the already-prepared formatting configuration, not every pending local E2E/accessibility change.
- Browser walkthrough used that production build, a temporary SQLite database, and deterministic test market data. No production records or paid AI calls were used.
- Login at 1440x900 and 390x844: Login and Guest buttons visible, email focusable, no horizontal overflow.
- Imported `testing/sample_portfolio_trades.csv`: 10 trades, 7 positions, successful dashboard navigation. Inspected all 12 main app routes, including risk, regime, health, recommendations, market, trades, portfolios, upload, stress tests, Copilot, and settings.
- All 12 routes passed the 390px horizontal-overflow check in light mode. Desktop walkthrough used dark mode. This is not a complete accessibility, Safari, zoom, or touch-device audit.
- Stress test: a -15% market shock changed the fixture portfolio from INR 132,773.44 to INR 112,857.42, matching the sensitivity calculation.
- Copilot returned a clearly labeled local fallback with no configured external key. Live NVIDIA credentials, provider latency, and model availability were not verified.
- Direct code execution reproduced the health-score, date-alignment, and mixed-currency issues below.
- No deployed frontend/backend URL or hosting logs were supplied. Hosting-specific crashes, DNS, TLS, real cold starts, and deployed secrets remain unverified. The earlier localhost:3000 observation is not evidence about the deployed service.

## Priority Findings

### P1: Missing analytics can produce a reassuring health score

Evidence: `frontend/src/lib/analytics-derive.ts:37`, `:93`, `:99`, `:117`; `frontend/src/app/(app)/portfolio-health/page.tsx:27`.

`Number(null)` becomes zero. Missing inputs also receive synthetic component scores, and an absent regime earns data-availability credit. The health page does not gate the score on `hasData` or show query failures before rendering the report.

Reproductions using the actual function:

| Input | Output |
| --- | --- |
| No summary, positions, risk, or regime | 53/100, Aggressive, Stable; "Analytics inputs available"; no weaknesses |
| Null volatility, drawdown, and Sharpe | 70/100; volatility/drawdown components 100/100; "Stable volatility at 0.00%" |
| Six equal bank holdings | Diversification 100/100 despite one-sector concentration |

Change: reject null/blank/boolean values as missing; return an explicit unavailable/partial status; never substitute zero for an unknown risk metric. Show which inputs are absent and the next recovery action.

Acceptance: missing analytics never produce a normal numeric score or a claim that no weaknesses exist.

### P1: There are three incompatible health calculations

Evidence: `src/analytics/utils.py:96`, `src/analytics/returns_repository.py:58`, `frontend/src/lib/analytics-derive.ts:99`, `:365`.

The backend persists a drawdown/volatility/Sharpe score. The UI calculates a seven-component score. The health-history chart uses a third three-component formula. With 20% volatility, 15% drawdown, Sharpe 1, a 10% return, six equal holdings, and Bull regime, the backend gives 80 while the frontend gives 74. These are different definitions, not rounding differences.

The history also joins rolling volatility to cumulative returns by array index rather than date. A test with volatility available only on January 3 applied that volatility to January 1. Subsequent points used a fallback volatility. This introduces later information into earlier chart dates.

Change: one backend scoring service, a versioned response contract, and stored score snapshots. Remove the approximate trajectory until it represents the same calculation using information available on each date.

Acceptance: dashboard, health page, API, report, and Copilot use the same snapshot, period, formula version, and value.

### P1: The historical return path is not a reconstruction of the user's trades

Evidence: `src/analytics/analytics_service.py:232`, particularly `:244` and `:270`; `src/analytics/utils.py:15`.

The service selects today's open holdings, normalizes their remaining cost bases, and applies those fixed weights to every historical daily return. Holdings sold completely disappear from the path. Later purchases contribute to dates before they were owned. There is no historical cash ledger or treatment of changing quantities in this calculation.

That can be a useful hypothetical current-basket risk series, but the UI calls it compounded portfolio performance. It must not be mistaken for actual investor performance.

Separately, `src/portfolio/position_service.py:224` and `:248` expose unrealized gain divided by remaining cost basis as `total_return`, while `total_pnl` includes realized gains. The formula is meaningful for open positions, but the current labels imply a broader result.

Change: distinguish open-holding return, realized/unrealized P&L, and historical performance. Build a trade- and cash-flow-aware daily ledger before claiming actual time-weighted performance. Money-weighted return needs external cash-flow information; do not infer deposits and withdrawals blindly from trades. Keep hypothetical current-holdings risk separately labeled.

Acceptance: test staggered purchases, full exits, partial sales, fees, corporate actions, cash flows, and reopening a position. Closed profitable holdings must not vanish from performance history.

### P1: Analytics snapshots overwrite each other across calculation windows

Evidence: `src/analytics/returns_repository.py:38`, `:58`; `frontend/src/lib/api/analytics.ts:29`; `frontend/src/app/(app)/risk/page.tsx:88`.

Return/risk rows are upserted using portfolio and date without the start date, confidence level, rolling window, or formula version. A one-year request can overwrite an overlapping all-time cumulative return with a different starting point. A custom risk calculation can replace another calculation for the same end date.

The risk page defaults to one year, while dashboard/health risk requests default to the first trade. In the fixture walkthrough, risk showed 1.13% max drawdown while health showed 10.65%; the time windows differed. A user sees apparent disagreement without a shared period control.

Change: separate canonical daily ledger returns from parameterized analytics snapshots; key snapshots by calculation inputs and data revision. Do not persist arbitrary page calculations into a single canonical row. Use a shared period selector or explicit period labels on every card.

Acceptance: switching windows or confidence settings cannot corrupt stored all-time history; concurrent requests preserve both results.

### P1: Mixed currencies are accepted but not converted

Evidence: `src/portfolio/trade_service.py:40`, `:67`; `src/portfolio/csv_import_service.py:200`; `src/portfolio/position_service.py:252`.

Currencies are stored as labels while quantities, prices, costs, and proceeds are summed numerically. Directly supplying two same-symbol buys of 100 INR and 100 USD produces a cost basis of 200. Changing the base-currency label does not perform an FX conversion.

Change: for the MVP, explicitly restrict portfolios to supported single-currency instruments and reject mismatched trade/quote currencies. Offer multi-currency only with dated FX rates and conversion provenance. Preserve unknown quote currency as unknown rather than assuming it matches.

Acceptance: mixed-currency uploads fail clearly instead of producing plausible but dimensionally invalid values.

### P1: The shipped model cannot load under the current artifact contract

Evidence: `models/training_metadata.json`, `src/regime/model_utils.py:69`, `src/analytics/regime_service.py:17`, `render.yaml:45`.

The committed metadata lacks the schema/version contract now required by the loader. Executing the metadata validator returns `ModelArtifactError: HMM artifacts use an unsupported schema. Retrain the model with this release.` Render disables runtime fitting, so this combination falls back to deterministic rules unless compatible artifacts are supplied separately.

The fallback assigns a fixed 0.90 to the selected state (`src/analytics/regime_service.py:175`). This is not calibrated model confidence. Several recommendation confidences are also constants, for example 0.95 and 0.90 in `src/intelligence/recommendation_service.py:185`. They should not look like measured probabilities.

Change: train and ship compatible artifacts through a reproducible offline pipeline. Record model version and validation status. Keep deterministic fallback explicitly labeled, without a statistical-confidence percentage. Rename rule confidence to a qualitative evidence label until calibrated. Do not call all regime output HMM inference or real-time prediction.

Acceptance: build-time artifact-load test, out-of-sample evaluation report, and a visible distinction between trained model, rule fallback, missing features, and unavailable results. Do not enable the validation gate until a genuine report passes it.

### P1: Current deployment checks can turn green while the database is unusable

Evidence: `render.yaml:8`, `:9`, `:29`; `src/api/routes/system.py:23` and `:40`.

Render checks `/health`, which does not connect to the database. `/ready` checks the connection and migration revision, but is not the configured Render check. Automatic deployments are enabled without a CI-success gate in the blueprint, and startup migrations are disabled. No automatic release migration step is defined there.

Both local `.env` database URLs also fail SQLAlchemy URL parsing. They contain unfinished connection configuration. No values are reproduced here. A valid URL must be entered privately in local/hosting environment settings before database access can succeed.

Change: complete runtime and migration URLs privately; rotate previously disclosed credentials; serialize migrations once per release; deploy only the tested commit; make `/ready` the readiness gate. Keep `/health` for process liveness. Confirm rollback and database recovery on a separate staging branch.

For the free Render plan, do not assume a paid pre-deploy job or shell is available. A protected GitHub Actions migration step followed by a deploy hook is an option, with a least-privilege runtime role and a separate migration role. Use backward-compatible migrations because migration-before-release temporarily overlaps old code.

Acceptance: wrong password, missing migration, or unreachable database keeps readiness red; failed CI cannot release a new revision.

### P2: Database failure is presented as an empty account

Evidence: `frontend/src/lib/portfolio-context.tsx:23`; `frontend/src/components/layout/require-portfolio.tsx:24`.

Reproduced by returning HTTP 503 for the portfolio-list request: the dashboard says "Start with a portfolio" and asks the user to upload/create one. The context exposes the error, but the guard ignores it and treats missing data as an empty list.

Also, authentication hydration catches any `/me` failure and clears the remembered user (`frontend/src/lib/auth.tsx:108`), including a network outage rather than only an invalid session.

Change: separate loading, confirmed-empty, temporarily unavailable, stale-but-usable, and unauthenticated states. Keep a retry action and preserved input. Do not imply data was lost when it cannot be retrieved.

Acceptance: simulate offline, 503, timeout, 401, and a valid empty response; each must have distinct behavior.

### P2: Guest conversion and retention promises do not match the implementation

Evidence: `frontend/src/app/(auth)/signup/page.tsx:26`; `src/api/routes/auth.py:106`; `src/config/settings.py:64`; `src/auth/lifecycle.py:16`.

The upload screen encourages guests to create an account to keep their work. Navigating to `/signup` as a guest actually redirects back to `/dashboard`, reproduced in the browser. Signup creates a new user; no guest-portfolio conversion is performed.

Guest tokens live in tab storage, but backend data is retained separately. Defaults are 12 hours for the guest token and 24 hours from guest creation for cleanup eligibility, with periodic cleanup. Tab closure does not trigger guaranteed immediate backend deletion. Session restoration and duplicated tabs need explicit testing; tab storage alone is not server-side revocation.

Change: add a tested "Save this portfolio" account-conversion flow that retains ownership transactionally. Explain tab access separately from temporary backend retention. Offer explicit "End guest session and delete data". Do not rely on unload requests for guaranteed cleanup.

Acceptance: conversion preserves trades/analytics, account deletion removes owned data, expiration is enforced, and another principal cannot access the guest portfolio.

### P2: Optional market feeds can take down the whole market page

Evidence: `frontend/src/lib/api/market.ts:44`.

The market screen combines price history, quotes, VIX, flows, index data, and optional features with `Promise.all`. One unavailable optional feed rejects the entire snapshot, even when stock-price history succeeded.

Change: independently cache/query each feed or retain partial results with per-section errors. The landing tape currently uses a fixed list, not a movers ranking, and strips source/freshness metadata. Retain latest-known prices but label their timestamp and stale status. Do not imply exchange streaming when polling/cached quotes are used.

Acceptance: missing FII/DII does not blank stock prices or interrupt import/dashboard use.

### P2: Container frontend configuration misses the same-origin proxy

Evidence: `compose.staging.yaml:33`, `frontend/Dockerfile`, `frontend/next.config.ts:7` and `:67`.

The frontend supports `LATENT_API_ORIGIN`, but staging Compose does not pass it as a build argument. Using relative `/api/v1` without the rewrite gives missing API routes. Using separate Vercel/Render origins directly creates cross-site cookie concerns with the configured SameSite=Lax policy.

Change: standardize and test the documented same-origin `/api/v1` proxy path with an HTTPS backend origin. Pass the build argument through Compose too. Verify sign-up, login, refresh, remember-me, logout, and CSRF protections through the actual deployed proxy, not only direct localhost calls.

Acceptance: a production-build browser test using PostgreSQL and the deployed proxy passes for accounts as well as guests. Current Playwright configuration starts a dev frontend and a SQLite fixture backend (`frontend/playwright.config.ts:8`, `:60`).

## Health Score: Recommended Redesign

The current frontend is a weighted heuristic:

| Component | Weight | Current mapping, before rounding |
| --- | --- | --- |
| Return | 20% | `clamp(60 + 150 * return_fraction)` |
| Volatility | 18% | `clamp(100 - 220 * abs(volatility))` |
| Drawdown | 20% | `clamp(100 - 240 * abs(drawdown))` |
| Risk-adjusted return | 14% | `clamp(45 + 28 * Sharpe)` |
| Diversification | 14% | Top-position weight and holding count only |
| Regime | 9% | Fixed scores for Bull/Bear/High Volatility/Crisis |
| Data | 5% | Presence/length/fallback flags |

These weights and thresholds are not empirically established accuracy. A scalar health score has no accuracy percentage until its intended meaning and validation target are defined.

Recommended product definition: **a transparent review-priority indicator**, not the probability of making money, not a suitability certificate, and not a market forecast.

1. Fix ledger inputs and missing-data behavior before changing weights.
2. Compute it once on the backend. Return score/status, component contributions, missing inputs, period, as-of timestamp, price coverage, source freshness, and calculation version.
3. Separate **risk condition**, **fit to user preferences**, and **data confidence**. Poor coverage must qualify or suppress a score; it must not merely subtract five points.
4. Include sector concentration and effective holding count, not ticker count alone. Consider correlation only with adequate aligned history. Unknown sectors must reduce coverage, not imply diversification.
5. Avoid counting the same exposure repeatedly through return, Sharpe, volatility, drawdown, and regime. Test redundancy and sensitivity before selecting weights.
6. Show regime as context until validated. Bull should not automatically make a concentrated portfolio healthy, nor should every Bear label imply an unhealthy portfolio.
7. Use "Lower concern", "Review", and "High concern" rather than Conservative/Moderate/Aggressive, which can be mistaken for the user's selected risk tolerance. Establish thresholds through evidence, not cosmetic score distribution.
8. Replace synthetic historical health with point-in-time snapshots. Join all series on date. Store calculation version and input revision.
9. Predefine minimum history and coverage appropriate to each statistic. Very short windows must show an explicit limitation; a numeric result is not evidence of statistical reliability.
10. Validate using historical stress periods, diversified/concentrated portfolios, missing/stale prices, all-cash/all-sold states, and expert review. Use time-ordered holdouts; report stability, sensitivity, and whether higher concern actually corresponds to the defined adverse outcome. Do not fit and assess on the same samples.

A suggested response contract is `score: number | null`, `status: complete | partial | unavailable`, `components`, `coverage`, `missing_inputs`, `period`, `data_as_of`, `calculation_version`, and `model_mode`. The final component weights remain a product/research decision, not a number to choose to make the dashboard look better.

## Journey Changes and Removals

| Area | Friction | Proposed change | Measure |
| --- | --- | --- | --- |
| Landing | HMM/real-time language comes before a plain explanation; four entry actions compete | "Understand your portfolio's performance and risk." Make demo/import the main choices; sign-in secondary. Remove decorative status claims such as "Signal active" | First useful result reached, by entry route |
| Guest | User can explore but cannot save that work into an account | "Save this portfolio" with a safe conversion flow and clear retention | Guest-to-account conversion retaining the same portfolio |
| Import | Portfolio metadata comes before file selection; no obvious template download | File first, downloadable sample, auto-name; optional benchmark/description collapsed | Upload completion and median/p95 upload-to-result time |
| Import errors | Formatting repair exists, but a new file can race with an older preview response | Tie preview/repair to file identity or abort superseded requests; row-specific issues; preserve selected file on recoverable failure | Repair success, repeated submission rate |
| Dashboard | Too many equally weighted panels; next action is far below the primary figures | First screen: valuation, clearly defined P&L, one period, freshness/coverage, and one priority action. Sector exposure next. Details below | User can explain performance and next action in a short usability task |
| Dashboard charts | Headline open-holding return and historical model return can have opposite signs | Name each return precisely; use a consistent actual-performance series when implemented | Metric-comprehension task success |
| Risk | Twelve ratios and advanced inputs are exposed immediately | Default to largest fall, typical variability, and a clearly explained downside estimate; put advanced ratios/settings behind expansion | Time to answer "what risk should I review?" |
| Regime | Hidden-state IDs and 100% probabilities invite overconfidence | Plain current-state summary, why, model source, and limitations; advanced transition tables collapsed | Users distinguish state fit from predictive accuracy |
| Health | Label sounds authoritative despite an unvalidated formula | Rename/reposition as a review aid until calibrated; show the two largest contributors and data coverage | Correct explanation of what the score does and does not mean |
| Recommendations | Arbitrary confidence percentages; repeated general actions; "Mark read" is not completion | Remove uncalibrated percentages; show evidence, relevance to the user's profile, a concrete review action, and reviewed/dismissed state | Recommendation opened, reviewed, and understood |
| Copilot | On a 390px viewport the question box is about two screens down | Composer and useful starters first; connection/model/key controls under Advanced; short limitation disclosure with expandable detail | Question-to-grounded-answer success and latency |
| Copilot | No provider retry action beside a failed message; page state can retain history while changing portfolio | Preserve drafts, inline Retry, cancel option, portfolio-scoped chat; verify switching portfolios cannot mix context | Failed-response recovery; zero cross-portfolio context contamination |
| Stress tests | Defaults are interpreted even if the parser did not understand the request | Expose unrecognized text/default assumptions; keep confirmation; call it a sensitivity scenario, not an AI forecast | Users correctly predict what the scenario will change |
| Market data | Technical feed controls are prominent; one optional feed can fail the whole view | Advanced workspace; independent feeds; timestamps and cached/delayed indicators | Core workflow survives external-feed outages |
| Settings | API URL/database status precede useful preferences | Move diagnostics to Advanced; profile settings after the first result with "Why we ask"; allow skip | Profile completion without reducing first-result activation |
| Accounts | No password-reset/email-verification flow was found | Add recovery and verification before broad public account use; generic, rate-limited responses | Recovery completion, account-access support requests |
| Navigation | Twelve top-level destinations make exploration feel technical | Main: Overview, Holdings, Insights, Copilot. Group import/trades under Holdings and advanced risk/regime/stress/market views under Insights | Navigation errors and task-completion time |

Do not remove underlying analyses just to reduce visual density. Use progressive disclosure. Existing clear import states, theme support, explanatory metric controls, demo support, and stress confirmation are worth retaining.

## First Dashboard Proposal

1. Portfolio name, analysis period, and "Prices through [date]" with coverage status.
2. Current holdings value and clearly separated realized/unrealized P&L. Avoid calling remaining cost basis total invested capital without explanation.
3. One plain summary: what changed, the largest exposure, and the most useful thing to review next.
4. Sector allocation with selected-sector holdings; current market state with an honest model-source label.
5. One primary action such as "Review sector exposure". Copilot can explain that specific issue rather than starting from a blank chat.
6. Optional details for return history, risk measures, and methodology. Use a dismissible first-use guide, not mandatory popups on every visit.

Questions should affect an observable decision. Ask investment horizon, expected need for cash, and a understandable loss-comfort question only when they are used in recommendations. Do not collect preferences that the product ignores. Each helper explains the actual effect; allow "Not sure" and disclose defaults.

## Release and Reliability Work

- Commit the existing verified CI fixes as a coherent set, including newly referenced files. Re-run GitHub CI on that exact commit; local success is not a remote green run.
- Validate environment configuration without printing credentials. Use a parser and explicit placeholder detection, not repeated trial-and-error deployments.
- Use one same-origin API setup for deployment, and test the cookie/guest paths through it. Keep secrets server-side; confirm previously shared credentials are revoked without sending replacements in chat.
- Make release readiness check the database and schema, not just a running process. Use one migration owner; test restoration and rollback on a disposable database.
- Add production-build E2E with PostgreSQL. Keep fast SQLite unit tests, but add real concurrent-write, ownership, migration, session, and rate-limit integration tests.
- Add import idempotency and transactional boundaries. The current import commits trades before all post-import work finishes (`src/portfolio/csv_import_service.py:212`); test failures after commit so a retry cannot create confusing duplicates.
- Use a coherent portfolio snapshot with a valuation timestamp and revision. Avoid fetching/refreshing the same market data independently for summary, positions, risk, and AI.
- Bound external calls and report progressive state: importing, preparing analytics, cached results available, retrying provider. Do not silently change an unavailable answer into a confident default.
- Cache shared market data by ticker, source, and timestamp. Cache portfolio outputs by owner/portfolio/revision/parameters. Invalidate after trade changes. Avoid caching one user's AI response for another user.
- Keep rate limits, upload caps, scoped queries, cookie protections, secret checks, and audits. Also test them through the reverse proxy; per-IP limits depend on correct trusted-proxy handling. This review is not a penetration test.
- Add operational alerts for readiness failures, 5xx rate, repeated imports, provider fallbacks, missing-price coverage, and AI spend. Log correlation IDs and error codes, not CSV contents, passwords, tokens, or API keys.
- Put privacy/data-retention and an explicit educational-risk disclaimer in the release checklist. A disclaimer does not fix misleading numbers.

Render Free sleeps after 15 minutes idle and typically needs about a minute to restart; it has limited resources and ephemeral local storage. Render explicitly positions Free as a preview/hobby option rather than production hosting. This makes a zero-cost portfolio showcase feasible, but not a credible always-on uptime promise. Show a useful waking-up state and keep demo behavior honest; do not describe polling tricks as an uptime guarantee. [Render Free documentation](https://render.com/docs/free)

For a controlled CI-to-release path, Render supports secret deploy hooks and selecting a commit. Keep the hook in CI secrets, not repository files. [Render deploy hooks](https://render.com/docs/deploy-hooks)

## Acceptance Tests to Add

- Missing/null metrics produce no normal health score; missing prices cannot improve health.
- More sector/holding concentration does not improve diversification, all else equal.
- Future observations cannot affect an earlier point-in-time score; date alignment is explicit.
- Summary, health, report, and Copilot reconcile to one revision and period.
- Staggered buys, sales, full exits, fees, and supported corporate actions reconcile to a ledger.
- Currency mismatch is rejected until FX accounting is implemented.
- Parameter changes preserve canonical history; concurrent computations do not overwrite unrelated snapshots.
- Missing/corrupt model artifacts are detected before release; fallback never reports invented model confidence.
- Provider failure preserves useful market sections and gives actionable recovery.
- Database outage is not an empty account; transient `/me` failure is not silently treated as revoked credentials.
- Guest conversion preserves the portfolio; expiry/deletion and ownership isolation are checked.
- CSV file replacement cannot display another file's validation result; retry after a lost response is idempotent.
- Account login, remember-me, logout, recovery, and guest access work on deployed HTTPS origins in major browsers.
- Mobile keyboard does not cover the Copilot composer; focus order, reduced motion, touch help, contrast, and zoom are checked.

## Product Success Measures

Define activation as a successful import/demo followed by viewing a populated, explained dashboard, not merely creating an account. Track entry-route conversion, import failure category, time to first useful result (median and p95), metric comprehension in usability sessions, recommendation review, and grounded-answer success. Separate warm/cold latency and real/synthetic data. Establish baselines before choosing targets. Avoid collecting portfolio contents in analytics events.

## Recommended Order

1. Complete private configuration, commit CI fixes, and establish a gated staging release with database readiness.
2. Fix accounting definitions, snapshot identity, null handling, and the single health-score source.
3. Ship compatible model artifacts or explicitly position the release as rules-based; remove uncalibrated percentages.
4. Fix failure recovery, guest conversion, and import robustness.
5. Simplify dashboard/Copilot/navigation, then test comprehension with representative first-time users.
6. Validate the model and score out of sample; load-test the intended environment before making stronger production claims.

Do not defer the first four items in favor of more animations or additional AI surface area.
