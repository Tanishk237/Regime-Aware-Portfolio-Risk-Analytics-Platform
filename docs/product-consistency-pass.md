# Product consistency pass - 29 September 2026

## What changed

- The overview answers three questions in order: what do I own, where is the risk, and what should I review next? It uses one intelligence response, with secondary history behind an expandable section.
- Dashboard, portfolio detail, risk review, reports, and Copilot consume the backend risk-review definition. Removed the separate frontend score, estimated score history, and client-generated recommendations.
- Open-holding return is unrealized P&L divided by remaining purchase cost. Total P&L includes completed sales; these are deliberately separate values.
- Historical risk is a hypothetical, daily-rebalanced basket of current open holdings weighted by remaining cost. It is explicitly not actual investor performance or a cash-flow-aware backtest.
- Custom risk windows and assumptions no longer overwrite canonical return and risk snapshots. Regime analysis defaults to the dashboard snapshot and applies custom windows only on submission.
- Missing prices are not replaced with purchase costs in sector allocation. Missing metrics are not converted to zero. Incomplete evidence is visible.
- Rule-based regime fallback has no invented probability. HMM probabilities now correspond to the decoded state, rather than the highest posterior for a potentially different state. Rule recommendations no longer display arbitrary confidence percentages.
- Trade and import currency mismatches are rejected before mutation; a populated portfolio cannot be relabeled into another currency. Invalid/non-finite CSV numbers are rejected instead of silently coercing fees to zero.

## Risk-review contract

`src/analytics/health.py` owns `risk-review-v1`:

1. Start at 100.
2. Subtract `min(abs(max_drawdown) * 100, 40)`.
3. Subtract `min(annualized_volatility * 50, 30)`.
4. Add `clamp(sharpe * 5, -10, 10)`.
5. Clamp to 0-100 and round.

The existing backend weights were retained, not scientifically revalidated. The response includes the formula version, individual contributions, missing inputs, and observation count. At least 60 daily returns and all three finite, valid inputs are required. This is a conservative product gate, not proof of statistical sufficiency. The score is an uncalibrated review aid, not investment advice, a safety rating, or a predicted outcome. Concentration and data freshness remain separate checks, not hidden score bonuses.

## Journey and interface

- Flat themed surfaces, aligned sections, smaller headings, responsive spacing, and subtle motion that does not hide data while waiting for a scroll trigger.
- Shadcn inputs, buttons, accordions, accessible progress values, and named stepped regime timelines.
- Upload metadata is secondary to choosing and validating the CSV. Failed validation retains the file and provides retry. Old asynchronous previews cannot replace the newest selection.
- Account outages are distinct from empty accounts. Transient authentication hydration errors do not erase a remembered identity; API authorization still gates data access.
- Optional market-feed failures preserve successful feeds and show a warning. Both quote tapes can be paused, and stale quotes are labeled as stored prices.
- Copilot configuration is collapsed initially. Chat follows new responses, preserves the draft after failure, supports retry, and resets conversation state when portfolios change.

## Verification

- Backend: 187 tests passed using isolated test databases, including score guards, currency rejection, CSV validation, custom-window persistence protection, and regime probability semantics.
- Playwright: 10 tests passed. Includes adapter contracts; guest -> sample CSV -> dashboard -> risk -> regime -> stress -> risk review -> recommendations -> Copilot -> report -> settings; upload recovery; portfolio-list outage; optional market-feed outage; chat failure/retry and auto-scroll.
- Screenshots: login at 1440x900 and 390x844; dashboard in dark/light mobile themes; all main routes checked for horizontal overflow at 390px.
- Frontend lint, TypeScript, and optimized production build pass. Automated browser tests use a dev frontend; a separate production preview is used for the final visual walkthrough.

## Remaining release work

This pass is not a production or predictive-accuracy certification. No live Neon records, hosting settings, or provider credentials were changed.

- Validate deployed account cookies, proxy, migrations, ownership, and concurrent requests against PostgreSQL. Current browser fixtures use temporary SQLite databases and deterministic market data.
- Rotate previously disclosed credentials privately and complete the existing staging/readiness/CI work described in the release review.
- Produce compatible trained HMM artifacts and a real out-of-sample evaluation. Do not market state-fit probabilities as forecast accuracy.
- A real performance ledger still needs cash flows, historical positions, and corporate-action treatment. Multi-currency portfolios need dated FX rates and verified quote currencies; the new guards are not FX support.
- Guest data is temporarily backend-backed; tab closure does not guarantee immediate server deletion. Account conversion that preserves guest work remains separate work.
- Import idempotency and concurrent retry behavior, Safari/Firefox, zoom and assistive-technology audits, external AI provider failures, real-market coverage, and hosted cold-start/load testing still need release-environment verification.

## Product measures to collect next

Measure successful imports per attempt, time from landing to first useful overview, validation retry success, explanation usage, and guest completion of the first review. Record event outcomes and timings, not portfolio contents, prompts, or credentials. Compare those outcomes before adding further visual features.
