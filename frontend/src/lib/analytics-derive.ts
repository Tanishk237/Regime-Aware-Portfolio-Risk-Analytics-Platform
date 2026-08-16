import type { Severity } from '@/components/domain/finance';
import { toSeries } from '@/lib/format';
import type { PortfolioSummary, Position, RegimeAnalytics, RiskAnalytics } from '@/lib/types';

export type HealthComponent = {
	key: string;
	label: string;
	score: number;
	weight: number;
	detail: string;
};

export type RiskDriver = {
	id: string;
	title: string;
	severity: Severity;
	category: 'Risk' | 'Diversification' | 'Regime' | 'Performance' | 'Data Quality';
	description: string;
	metric: string;
	action: string;
};

export type HealthReport = {
	score: number;
	category: 'Conservative' | 'Moderate' | 'Aggressive' | 'High Risk' | 'Critical';
	trend: 'Improving' | 'Stable' | 'Deteriorating';
	components: HealthComponent[];
	drivers: RiskDriver[];
	strengths: string[];
	weaknesses: string[];
	history: Array<{ date: string; value: number }>;
	hasData: boolean;
};

const clamp = (value: number, min = 0, max = 100) => Math.max(min, Math.min(max, value));

function num(value: unknown): number | undefined {
	const parsed = typeof value === 'number' ? value : Number(value);
	return Number.isFinite(parsed) ? parsed : undefined;
}

export function metric(risk: RiskAnalytics | undefined, ...names: string[]): number | undefined {
	const metrics = risk?.metrics;
	if (!metrics) return undefined;
	for (const name of names) {
		const direct = num(metrics[name]);
		if (direct !== undefined) return direct;
	}
	const lowered = Object.fromEntries(
		Object.entries(metrics).map(([key, value]) => [key.toLowerCase(), value])
	);
	for (const name of names) {
		const value = num(lowered[name.toLowerCase()]);
		if (value !== undefined) return value;
	}
	return undefined;
}

export function largestWeight(
	positions: Position[]
): { ticker: string; weight: number } | undefined {
	if (positions.length === 0) return undefined;
	const totalValue = positions.reduce((sum, p) => sum + (p.market_value ?? 0), 0);
	const enriched = positions.map((p) => ({
		ticker: p.ticker,
		weight: p.weight ?? (totalValue > 0 ? (p.market_value ?? 0) / totalValue : 0)
	}));
	return enriched.sort((a, b) => b.weight - a.weight)[0];
}

export function buildHealthReport(input: {
	summary?: PortfolioSummary;
	positions?: Position[];
	risk?: RiskAnalytics;
	regime?: RegimeAnalytics;
}): HealthReport {
	const { summary, positions = [], risk, regime } = input;

	const cagr = metric(risk, 'cagr', 'annualized_return');
	const totalReturn = metric(risk, 'total_return') ?? summary?.total_return;
	const volatility = metric(risk, 'annualized_volatility', 'volatility');
	const maxDrawdown = metric(risk, 'max_drawdown');
	const sharpe = metric(risk, 'sharpe_ratio', 'sharpe');
	const sortino = metric(risk, 'sortino_ratio', 'sortino');
	const varHist = metric(risk, 'historical_var', 'var_historical');
	const cvarHist = metric(risk, 'historical_cvar', 'cvar_historical');
	const drawdownSeries = toSeries(risk?.series?.drawdown);
	const rollingVol = toSeries(risk?.series?.rolling_volatility);
	const rollingReturns = toSeries(risk?.series?.rolling_returns);
	const cumulative = toSeries(risk?.series?.cumulative_returns);

	const hasData = Boolean(risk?.metrics || positions.length > 0);

	const top = largestWeight(positions);
	const concentration = top?.weight ?? 0;
	const distinct = positions.filter((p) => (p.quantity ?? 0) !== 0).length;

	const returnScore = totalReturn === undefined ? 55 : clamp(60 + totalReturn * 100 * 1.5);
	const volScore = volatility === undefined ? 55 : clamp(100 - Math.abs(volatility) * 100 * 2.2);
	const ddScore = maxDrawdown === undefined ? 55 : clamp(100 - Math.abs(maxDrawdown) * 100 * 2.4);
	const riskAdjScore = sharpe === undefined ? 55 : clamp(45 + sharpe * 28);
	const diversificationScore =
		positions.length === 0
			? 40
			: clamp(100 - Math.max(0, concentration - 0.25) * 160 - Math.max(0, 6 - distinct) * 5);
	const regimeKeyName = (regime?.current_regime ?? 'unknown').toLowerCase();
	const regimeScore = regimeKeyName.includes('bull')
		? 88
		: regimeKeyName.includes('bear')
			? 32
			: regimeKeyName.includes('vol')
				? 48
				: regimeKeyName.includes('crisis')
					? 18
					: 55;
	const dataScore = clamp(
		30 +
			(risk?.metrics ? 30 : 0) +
			(drawdownSeries.length > 20 ? 20 : drawdownSeries.length) +
			(regime?.fallback_used ? 0 : 20)
	);

	const components: HealthComponent[] = [
		{
			key: 'return',
			label: 'Return Health',
			score: Math.round(returnScore),
			weight: 0.2,
			detail:
				totalReturn === undefined
					? 'Total return unavailable.'
					: `Total return ${(totalReturn * 100).toFixed(2)}%`
		},
		{
			key: 'volatility',
			label: 'Volatility Health',
			score: Math.round(volScore),
			weight: 0.18,
			detail:
				volatility === undefined
					? 'Volatility unavailable.'
					: `Annualised volatility ${(volatility * 100).toFixed(2)}%`
		},
		{
			key: 'drawdown',
			label: 'Drawdown Health',
			score: Math.round(ddScore),
			weight: 0.2,
			detail:
				maxDrawdown === undefined
					? 'Max drawdown unavailable.'
					: `Max drawdown ${(Math.abs(maxDrawdown) * 100).toFixed(2)}%`
		},
		{
			key: 'riskadj',
			label: 'Risk-Adjusted Health',
			score: Math.round(riskAdjScore),
			weight: 0.14,
			detail: sharpe === undefined ? 'Sharpe unavailable.' : `Sharpe ${sharpe.toFixed(2)}`
		},
		{
			key: 'diversification',
			label: 'Diversification Health',
			score: Math.round(diversificationScore),
			weight: 0.14,
			detail:
				positions.length === 0
					? 'No open positions.'
					: `${distinct} holdings, top weight ${(concentration * 100).toFixed(2)}%`
		},
		{
			key: 'regime',
			label: 'Regime Health',
			score: Math.round(regimeScore),
			weight: 0.09,
			detail: `Current regime ${regime?.current_regime ?? 'unknown'}`
		},
		{
			key: 'data',
			label: 'Data Health',
			score: Math.round(dataScore),
			weight: 0.05,
			detail: regime?.fallback_used
				? 'Regime fallback labeller in use.'
				: 'Analytics inputs available.'
		}
	];

	const score = Math.round(
		components.reduce((sum, c) => sum + c.score * c.weight, 0) /
			components.reduce((sum, c) => sum + c.weight, 0)
	);

	const category: HealthReport['category'] =
		score >= 80
			? 'Conservative'
			: score >= 65
				? 'Moderate'
				: score >= 50
					? 'Aggressive'
					: score >= 35
						? 'High Risk'
						: 'Critical';

	const recentDrawdown = drawdownSeries.slice(-5).map((d) => Math.abs(d.value));
	const olderDrawdown = drawdownSeries.slice(-15, -5).map((d) => Math.abs(d.value));
	const avg = (values: number[]) =>
		values.length ? values.reduce((a, b) => a + b, 0) / values.length : undefined;
	const recentAvg = avg(recentDrawdown);
	const olderAvg = avg(olderDrawdown);
	const trend: HealthReport['trend'] =
		recentAvg === undefined || olderAvg === undefined
			? 'Stable'
			: recentAvg < olderAvg * 0.9
				? 'Improving'
				: recentAvg > olderAvg * 1.1
					? 'Deteriorating'
					: 'Stable';

	const drivers: RiskDriver[] = [];
	if (maxDrawdown !== undefined && Math.abs(maxDrawdown) > 0.15) {
		drivers.push({
			id: 'drawdown',
			title: 'Max drawdown is elevated',
			severity: Math.abs(maxDrawdown) > 0.25 ? 'high' : 'medium',
			category: 'Risk',
			description:
				'Your portfolio has experienced a significant peak-to-trough decline over the analysed window.',
			metric: `Max drawdown ${(Math.abs(maxDrawdown) * 100).toFixed(2)}%`,
			action: 'Review position sizing and downside protection.'
		});
	}
	if (volatility !== undefined && volatility > 0.22) {
		drivers.push({
			id: 'volatility',
			title: 'Volatility is running high',
			severity: volatility > 0.32 ? 'high' : 'medium',
			category: 'Risk',
			description: 'Realised volatility is above a typical long-only equity comfort band.',
			metric: `Annualised volatility ${(volatility * 100).toFixed(2)}%`,
			action: 'Consider trimming high-beta exposure or staggering new entries.'
		});
	}
	if (concentration > 0.35) {
		drivers.push({
			id: 'concentration',
			title: 'Position concentration is high',
			severity: concentration > 0.5 ? 'high' : 'medium',
			category: 'Diversification',
			description: `${top?.ticker ?? 'One holding'} contributes a large share of portfolio exposure.`,
			metric: `Top weight ${(concentration * 100).toFixed(2)}%`,
			action: 'Consider reducing concentration or adding diversifying assets.'
		});
	}
	if (
		regimeKeyName.includes('bear') ||
		regimeKeyName.includes('vol') ||
		regimeKeyName.includes('crisis')
	) {
		drivers.push({
			id: 'regime',
			title: `Portfolio is in ${regime?.current_regime} regime`,
			severity:
				regimeKeyName.includes('crisis') || regimeKeyName.includes('bear') ? 'high' : 'medium',
			category: 'Regime',
			description: 'Current regime probability suggests elevated uncertainty.',
			metric: `Confidence ${((regime?.confidence ?? regime?.probability ?? 0) * 100).toFixed(2)}%`,
			action: 'Monitor volatility and avoid oversized new positions.'
		});
	}
	if (sharpe !== undefined && sharpe < 0.5) {
		drivers.push({
			id: 'sharpe',
			title: 'Sharpe ratio is weak',
			severity: sharpe < 0 ? 'high' : 'medium',
			category: 'Performance',
			description: 'Returns are low relative to the volatility being taken.',
			metric: `Sharpe ${sharpe.toFixed(2)}`,
			action: 'Review underperforming holdings.'
		});
	}
	if (sortino !== undefined && sortino < 0.5) {
		drivers.push({
			id: 'sortino',
			title: 'Downside-adjusted return is weak',
			severity: 'medium',
			category: 'Performance',
			description: 'Sortino ratio suggests losses are not being compensated by upside.',
			metric: `Sortino ${sortino.toFixed(2)}`,
			action: 'Reassess holdings with persistent negative skew.'
		});
	}
	if (rollingReturns.length > 0 && (rollingReturns.at(-1)?.value ?? 0) < 0) {
		drivers.push({
			id: 'rolling',
			title: 'Rolling return is negative',
			severity: 'low',
			category: 'Performance',
			description: 'The latest rolling window return is below zero.',
			metric: `Rolling return ${((rollingReturns.at(-1)?.value ?? 0) * 100).toFixed(2)}%`,
			action: 'Watch for continuation before adding exposure.'
		});
	}
	if (cvarHist !== undefined && Math.abs(cvarHist) > 0.03) {
		drivers.push({
			id: 'cvar',
			title: 'Tail risk (CVaR) is elevated',
			severity: Math.abs(cvarHist) > 0.05 ? 'high' : 'medium',
			category: 'Risk',
			description: 'Average loss beyond the VaR threshold is large relative to portfolio value.',
			metric: `CVaR ${(Math.abs(cvarHist) * 100).toFixed(2)}% · VaR ${
				varHist === undefined ? '—' : `${(Math.abs(varHist) * 100).toFixed(2)}%`
			}`,
			action: 'Size positions for tail scenarios, not just average days.'
		});
	}
	if (regime?.fallback_used) {
		drivers.push({
			id: 'fallback',
			title: 'Regime model is using the deterministic fallback',
			severity: 'low',
			category: 'Data Quality',
			description:
				'Trained HMM artifacts were unavailable, so a deterministic fallback labeller produced these regimes.',
			metric: 'Regime source: fallback',
			action: 'Treat regime output as indicative and refresh market data.'
		});
	}
	if (!risk?.metrics) {
		drivers.push({
			id: 'data',
			title: 'Market data may be stale',
			severity: 'low',
			category: 'Data Quality',
			description: 'Some analytics rely on the latest stored market prices.',
			metric: 'Risk analytics unavailable',
			action: 'Refresh market data and re-run analytics.'
		});
	}

	const strengths: string[] = [];
	if (cagr !== undefined && cagr > 0)
		strengths.push(`Positive CAGR at ${(cagr * 100).toFixed(2)}%`);
	if (maxDrawdown !== undefined && Math.abs(maxDrawdown) <= 0.12)
		strengths.push(`Contained drawdown at ${(Math.abs(maxDrawdown) * 100).toFixed(2)}%`);
	if (sharpe !== undefined && sharpe >= 1)
		strengths.push(`Strong Sharpe ratio of ${sharpe.toFixed(2)}`);
	if (distinct >= 8 && concentration < 0.25) strengths.push('Well diversified holdings');
	if (regimeKeyName.includes('bull')) strengths.push('Constructive Bull regime backdrop');
	if (volatility !== undefined && volatility < 0.15)
		strengths.push(`Stable volatility at ${(volatility * 100).toFixed(2)}%`);
	if (rollingVol.length > 25) strengths.push('Sufficient history for rolling analytics');

	const weaknesses: string[] = [];
	if (concentration > 0.3) weaknesses.push(`Concentration risk in ${top?.ticker ?? 'top holding'}`);
	if (sortino !== undefined && sortino < 0.5)
		weaknesses.push(`Poor Sortino ratio (${sortino.toFixed(2)})`);
	if (maxDrawdown !== undefined && Math.abs(maxDrawdown) > 0.2)
		weaknesses.push(`Large max drawdown (${(Math.abs(maxDrawdown) * 100).toFixed(2)}%)`);
	if (volatility !== undefined && volatility > 0.25) weaknesses.push('Rising volatility');
	if (totalReturn !== undefined && totalReturn < 0) weaknesses.push('Negative total return');
	if (positions.length > 0 && distinct < 4) weaknesses.push('Very few holdings');

	// Approximate historical health from the drawdown / volatility series.
	const history = cumulative.length
		? cumulative.map((point, index) => {
				const dd = Math.abs(drawdownSeries[index]?.value ?? 0);
				const vol = Math.abs(rollingVol[index]?.value ?? volatility ?? 0.18);
				const ret = point.value;
				const approx =
					0.4 * clamp(100 - dd * 100 * 2.4) +
					0.3 * clamp(100 - vol * 100 * 2.2) +
					0.3 * clamp(60 + ret * 100 * 1.5);
				return { date: point.date, value: Math.round(approx) };
			})
		: [];

	return {
		score,
		category,
		trend,
		components,
		drivers,
		strengths,
		weaknesses,
		history,
		hasData
	};
}

export type Recommendation = RiskDriver & { created_at: string };

export function buildRecommendations(report: HealthReport): Recommendation[] {
	const now = new Date().toISOString();
	const order: Record<Severity, number> = { high: 0, medium: 1, low: 2 };
	return [...report.drivers]
		.sort((a, b) => order[a.severity] - order[b.severity])
		.map((driver) => ({ ...driver, created_at: now }));
}
