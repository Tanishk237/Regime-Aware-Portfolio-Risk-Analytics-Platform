import { expect, test } from '@playwright/test';
import { adaptPosition, adaptRegime, adaptRisk, normalizeSeries } from '../src/lib/api/adapters';

test('missing numeric evidence is never displayed as zero or cost weight', () => {
	const position = adaptPosition({ ticker: 'INFY.NS', quantity: 1, cost_weight: 0.8 });
	expect(position.market_weight).toBeUndefined();
	expect(position.unrealized_pnl).toBeUndefined();
	const series = normalizeSeries([
		{ date: '2026-01-01', value: null },
		{ date: '2026-01-02', value: 0 },
		{ date: '2026-01-03', value: Infinity },
		{ date: '2026-01-04', value: '' }
	]);
	expect(series).toEqual([{ date: '2026-01-02', value: 0 }]);
});

test('risk fractions and backend review survive adaptation unchanged', () => {
	const review = { score: 75, calculation_version: 'risk-review-v1' };
	const risk = adaptRisk({
		metrics: { total_return: -0.1305 },
		review,
		methodology: { observations: 120 }
	});
	expect(risk.metrics.total_return).toBe(-0.1305);
	expect(risk.review).toEqual(review);
	expect(risk.methodology?.observations).toBe(120);
});

test('feature fallback is not mistaken for a rule-based model', () => {
	expect(
		adaptRegime({ feature_metadata: { fallback_used: true, model_fallback_used: false } })
			.fallback_used
	).toBe(false);
	expect(
		adaptRegime({ regime_probability: null, feature_metadata: { model_fallback_used: true } })
			.regime_probability
	).toBeUndefined();
});
