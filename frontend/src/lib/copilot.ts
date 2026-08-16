import { buildHealthReport, buildRecommendations, metric } from '@/lib/analytics-derive';
import { formatCurrency, formatPercent, formatRisk } from '@/lib/format';
import type { PortfolioSummary, Position, RegimeAnalytics, RiskAnalytics } from '@/lib/types';

export type CopilotContext = {
	summary?: PortfolioSummary;
	positions: Position[];
	risk?: RiskAnalytics;
	regime?: RegimeAnalytics;
};

export const REPORT_TYPES = [
	'Daily Report',
	'Weekly Report',
	'Monthly Report',
	'Portfolio Summary',
	'Risk Summary',
	'Regime Summary',
	'Stress Test Report'
];

export const COPILOT_STARTERS = [
	'Explain my portfolio risk in plain English.',
	'What are the top risk drivers?',
	'Explain the current regime and confidence.',
	'What should I review before adding capital?'
];

export function buildCopilotResponse(context: CopilotContext, question?: string) {
	const health = buildHealthReport(context);
	const recommendations = buildRecommendations(health);
	const currency = context.summary?.base_currency ?? 'INR';
	const topPositions = [...context.positions]
		.sort((a, b) => (b.weight ?? 0) - (a.weight ?? 0))
		.slice(0, 5)
		.map((position) => `- ${position.ticker}: ${formatPercent(position.weight)}`)
		.join('\n');
	const topDrivers = recommendations
		.slice(0, 5)
		.map(
			(item) =>
				`- **${item.severity.toUpperCase()} ${item.category}**: ${item.title}. ${item.action}`
		)
		.join('\n');

	return [
		question ? `## Answer\n${answerLead(question)}\n` : '',
		'## Portfolio Snapshot',
		`- Current value: **${formatCurrency(context.summary?.current_value, currency)}**`,
		`- Invested value: **${formatCurrency(context.summary?.invested_value, currency)}**`,
		`- Total P&L: **${formatCurrency(context.summary?.total_pnl, currency)}**`,
		`- Total return: **${formatPercent(context.summary?.total_return)}**`,
		`- Health score: **${health.score}/100** (${health.category}, ${health.trend})`,
		'',
		'## Risk',
		`- CAGR: **${formatPercent(metric(context.risk, 'cagr'))}**`,
		`- Annualized volatility: **${formatPercent(metric(context.risk, 'annualized_volatility'))}**`,
		`- Max drawdown: **${formatPercent(metric(context.risk, 'max_drawdown'))}**`,
		`- Sharpe: **${formatRisk(metric(context.risk, 'sharpe'))}**`,
		`- Historical VaR: **${formatPercent(metric(context.risk, 'historical_var'))}**`,
		`- Historical CVaR: **${formatPercent(metric(context.risk, 'historical_cvar'))}**`,
		'',
		'## Regime',
		`- Current regime: **${context.regime?.current_regime ?? 'Unknown'}**`,
		`- Confidence: **${formatPercent(context.regime?.confidence ?? context.regime?.probability)}**`,
		`- Hidden state: **${context.regime?.current_state ?? '-'}**`,
		'',
		'## Concentration',
		topPositions || '- No positions available.',
		'',
		'## Recommended Actions',
		topDrivers || '- No active recommendation drivers detected.'
	].join('\n');
}

export function buildReport(context: CopilotContext, reportType: string) {
	return [`# ${reportType}`, '', buildCopilotResponse(context)].join('\n');
}

function answerLead(question: string) {
	const lower = question.toLowerCase();
	if (lower.includes('regime'))
		return 'The current regime view should be read alongside confidence and recent risk path.';
	if (lower.includes('risk'))
		return 'The most important risk read comes from drawdown, volatility, tail risk, and concentration together.';
	if (lower.includes('capital') || lower.includes('add'))
		return 'Before adding capital, check whether the regime and drawdown trend support taking more exposure.';
	return 'Here is the portfolio-aware answer using the latest backend analytics available in this dashboard.';
}
