import type {
	FeatureMatrix,
	FiiDiiFlowPoint,
	HistoricalPricePoint,
	LivePricePoint,
	Portfolio,
	PortfolioReturn,
	PortfolioSummary,
	Position,
	RegimeAnalytics,
	RiskAnalytics,
	Trade
} from '@/lib/types';

export function asArray<T>(value: unknown): T[] {
	if (Array.isArray(value)) return value as T[];
	if (value && typeof value === 'object') {
		const record = value as Record<string, unknown>;
		for (const key of ['items', 'results', 'data', 'portfolios', 'trades', 'positions']) {
			if (Array.isArray(record[key])) return record[key] as T[];
		}
	}
	return [];
}

export function asRecord(value: unknown): Record<string, unknown> {
	return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function stringId(value: unknown): string {
	return value === undefined || value === null ? '' : String(value);
}

function maybeString(value: unknown): string | null | undefined {
	return value === undefined ? undefined : value === null ? null : String(value);
}

function maybeNumber(value: unknown): number | null | undefined {
	if (value === undefined) return undefined;
	if (value === null) return null;
	const parsed = typeof value === 'number' ? value : Number(value);
	return Number.isFinite(parsed) ? parsed : null;
}

function optionalString(value: unknown): string | undefined {
	return maybeString(value) ?? undefined;
}

function optionalNumber(value: unknown): number | undefined {
	return maybeNumber(value) ?? undefined;
}

function numberOrZero(value: unknown): number {
	return maybeNumber(value) ?? 0;
}

export function normalizeSeries(value: unknown, valueKey = 'value') {
	if (Array.isArray(value)) {
		return value
			.map((item) => {
				const row = asRecord(item);
				return {
					date: String(row['date'] ?? ''),
					value: numberOrZero(row[valueKey] ?? row['value'])
				};
			})
			.filter((row) => row.date);
	}
	const record = asRecord(value);
	return Object.entries(record).map(([date, val]) => ({ date, value: numberOrZero(val) }));
}

export function adaptPortfolio(value: unknown): Portfolio {
	const row = asRecord(value);
	return {
		id: stringId(row['id']),
		user_id: optionalString(row['user_id']),
		name: String(row['name'] ?? 'Untitled portfolio'),
		description: maybeString(row['description']),
		base_currency: maybeString(row['base_currency']) ?? 'INR',
		benchmark: maybeString(row['benchmark']) ?? 'NIFTY50',
		created_at: maybeString(row['created_at']),
		updated_at: maybeString(row['updated_at'])
	};
}

export function adaptTrade(value: unknown): Trade {
	const row = asRecord(value);
	return {
		id: stringId(row['id']),
		portfolio_id: optionalString(row['portfolio_id']),
		ticker: String(row['ticker'] ?? '').toUpperCase(),
		transaction_type: row['transaction_type'] === 'SELL' ? 'SELL' : 'BUY',
		quantity: numberOrZero(row['quantity']),
		price: numberOrZero(row['price']),
		transaction_date: String(row['transaction_date'] ?? ''),
		broker: maybeString(row['broker']),
		fees: maybeNumber(row['fees']) ?? 0,
		taxes: maybeNumber(row['taxes']) ?? 0,
		currency: maybeString(row['currency']) ?? 'INR',
		notes: maybeString(row['notes'])
	};
}

export function adaptPosition(value: unknown): Position {
	const row = asRecord(value);
	const marketWeight = maybeNumber(row['market_weight']);
	const costWeight = maybeNumber(row['cost_weight']);
	const avgCost = maybeNumber(row['avg_cost']);
	return {
		id: optionalString(row['id']),
		portfolio_id: optionalString(row['portfolio_id']),
		ticker: String(row['ticker'] ?? '').toUpperCase(),
		quantity: numberOrZero(row['quantity']),
		average_cost: avgCost,
		avg_cost: avgCost,
		current_price: maybeNumber(row['current_price']),
		market_value: maybeNumber(row['market_value']),
		cost_basis: maybeNumber(row['cost_basis']),
		unrealized_pnl: maybeNumber(row['unrealized_pnl']) ?? 0,
		realized_pnl: maybeNumber(row['realized_pnl']) ?? 0,
		weight: marketWeight ?? costWeight,
		market_weight: marketWeight,
		cost_weight: costWeight,
		updated_at: maybeString(row['updated_at'])
	};
}

export function adaptPortfolioReturn(value: unknown): PortfolioReturn {
	const row = asRecord(value);
	return {
		id: optionalString(row['id']),
		portfolio_id: optionalString(row['portfolio_id']),
		date: String(row['date'] ?? ''),
		daily_return: numberOrZero(row['daily_return']),
		cumulative_return: maybeNumber(row['cumulative_return']),
		portfolio_value: maybeNumber(row['portfolio_value']),
		created_at: maybeString(row['created_at'])
	};
}

export function adaptSummary(value: unknown): PortfolioSummary {
	const row = asRecord(value);
	const unrealized = maybeNumber(row['unrealized_profit']) ?? maybeNumber(row['unrealized_pnl']);
	const realized = maybeNumber(row['realized_profit']) ?? maybeNumber(row['realized_pnl']) ?? 0;
	return {
		portfolio_id: optionalString(row['portfolio_id']),
		name: optionalString(row['name']),
		base_currency: maybeString(row['base_currency']) ?? 'INR',
		benchmark: optionalString(row['benchmark']),
		invested_value: maybeNumber(row['invested_value']) ?? 0,
		current_value: optionalNumber(row['current_value']),
		total_pnl: unrealized === null ? realized : (unrealized ?? 0) + realized,
		unrealized_pnl: optionalNumber(row['unrealized_profit'] ?? row['unrealized_pnl']),
		realized_pnl: realized,
		latest_return: optionalNumber(row['latest_return']),
		total_return: optionalNumber(row['total_return'] ?? row['unrealized_profit_pct']),
		position_count: maybeNumber(row['positions_count']) ?? maybeNumber(row['position_count']) ?? 0,
		trade_count: maybeNumber(row['trades_count']) ?? maybeNumber(row['trade_count']) ?? 0,
		positions_count: maybeNumber(row['positions_count']) ?? maybeNumber(row['position_count']) ?? 0,
		trades_count: maybeNumber(row['trades_count']) ?? maybeNumber(row['trade_count']) ?? 0
	};
}

export function adaptRisk(value: unknown): RiskAnalytics {
	const row = asRecord(value);
	const series = asRecord(row['series']);
	const returns = normalizeSeries(row['returns'], 'daily_return');
	const pnl = asRecord(row['pnl']);
	return {
		success: row['success'] !== false,
		portfolio_id: optionalString(row['portfolio_id']),
		as_of: optionalString(row['as_of']),
		returns,
		metrics: asRecord(row['metrics']) as Record<string, number | null>,
		pnl: {
			cost_basis: maybeNumber(pnl['cost_basis']) ?? 0,
			total_cost_basis: maybeNumber(pnl['cost_basis']) ?? 0,
			market_value: maybeNumber(pnl['market_value']) ?? undefined,
			realized_pnl: maybeNumber(pnl['realized_pnl']) ?? 0,
			unrealized_pnl: maybeNumber(pnl['unrealized_pnl']) ?? undefined,
			total_pnl: maybeNumber(pnl['total_pnl']) ?? undefined,
			positions: asArray<unknown>(pnl['positions']).map(adaptPosition)
		},
		series: {
			daily_returns: normalizeSeries(series['daily_returns'] ?? row['returns'], 'daily_return'),
			cumulative_returns: normalizeSeries(series['cumulative_returns'], 'cumulative_return'),
			drawdown: normalizeSeries(series['drawdown'], 'drawdown'),
			rolling_returns: normalizeSeries(series['rolling_returns'], 'rolling_return'),
			rolling_volatility: normalizeSeries(series['rolling_volatility'], 'rolling_volatility')
		}
	};
}

export function adaptRegime(value: unknown): RegimeAnalytics {
	const row = asRecord(value);
	const history = asArray<unknown>(row['regime_history'] ?? row['history']).map((item) => {
		const h = asRecord(item);
		return {
			date: String(h['date'] ?? ''),
			hidden_state: numberOrZero(h['hidden_state']),
			label: maybeString(h['regime_label'] ?? h['label']) ?? undefined,
			regime_label: maybeString(h['regime_label'] ?? h['label']) ?? undefined,
			probability: maybeNumber(h['probability']) ?? undefined
		};
	});
	const statistics = asArray<unknown>(row['regime_statistics'] ?? row['statistics']).map((item) => {
		const stat = asRecord(item);
		const label = maybeString(stat['regime_label'] ?? stat['label']) ?? undefined;
		return {
			hidden_state: numberOrZero(stat['hidden_state']),
			label,
			regime_label: label,
			sample_count: numberOrZero(stat['sample_count']),
			avg_return: optionalNumber(stat['average_return'] ?? stat['avg_return']),
			average_return: maybeNumber(stat['average_return'] ?? stat['avg_return']),
			avg_volatility: optionalNumber(stat['average_volatility'] ?? stat['avg_volatility']),
			average_volatility: maybeNumber(stat['average_volatility'] ?? stat['avg_volatility']),
			avg_drawdown: optionalNumber(stat['average_drawdown'] ?? stat['avg_drawdown']),
			average_drawdown: maybeNumber(stat['average_drawdown'] ?? stat['avg_drawdown']),
			avg_vix: optionalNumber(stat['average_vix'] ?? stat['avg_vix']),
			average_vix: maybeNumber(stat['average_vix'] ?? stat['avg_vix'])
		};
	});
	const durations = asArray<unknown>(row['regime_duration'] ?? row['durations']).map((item) => {
		const duration = asRecord(item);
		const state = numberOrZero(duration['hidden_state']);
		return {
			hidden_state: state,
			label: maybeString(asRecord(row['state_labels'])[String(state)]) ?? undefined,
			start_date: String(duration['start_date'] ?? ''),
			end_date: String(duration['end_date'] ?? ''),
			duration_days: numberOrZero(duration['duration_days'])
		};
	});
	const probability = maybeNumber(row['regime_probability'] ?? row['probability']);
	return {
		success: row['success'] !== false,
		portfolio_id: optionalString(row['portfolio_id']),
		tickers: asArray<string>(row['tickers']),
		current_regime: maybeString(row['current_regime']) ?? undefined,
		current_state: maybeNumber(row['current_state']) ?? undefined,
		confidence: probability ?? undefined,
		probability: probability ?? undefined,
		regime_probability: probability ?? undefined,
		transition_matrix: asArray<number[]>(row['transition_matrix']),
		state_labels: asRecord(row['state_labels']) as Record<string, string>,
		feature_metadata: asRecord(row['feature_metadata']),
		history,
		regime_history: history,
		statistics,
		regime_statistics: statistics,
		durations,
		regime_duration: durations,
		fallback_used: Boolean(
			asRecord(row['feature_metadata'])['fallback_used'] ||
			asRecord(row['feature_metadata'])['model_fallback_used']
		)
	};
}

export function adaptHistoricalPrice(value: unknown): HistoricalPricePoint {
	const row = asRecord(value);
	return {
		ticker: String(row['ticker'] ?? '').toUpperCase(),
		date: String(row['date'] ?? ''),
		open: maybeNumber(row['open']),
		high: maybeNumber(row['high']),
		low: maybeNumber(row['low']),
		close: numberOrZero(row['close']),
		volume: maybeNumber(row['volume'])
	};
}

export function adaptLivePrice(value: unknown): LivePricePoint {
	const row = asRecord(value);
	return {
		ticker: String(row['ticker'] ?? '').toUpperCase(),
		price: numberOrZero(row['price']),
		name: maybeString(row['name'])
	};
}

export function adaptFeatureMatrix(value: unknown): FeatureMatrix {
	const row = asRecord(value);
	return {
		tickers: asArray<string>(row['tickers']),
		start_date: String(row['start_date'] ?? ''),
		end_date: maybeString(row['end_date']),
		columns: asArray<string>(row['columns']),
		records: asArray<unknown>(row['records']).map((record) => {
			const item = asRecord(record);
			return {
				date: String(item['date'] ?? ''),
				values: asRecord(item['values']) as Record<string, number>
			};
		}),
		metadata: asRecord(row['metadata']),
		validation: asRecord(row['validation']) as FeatureMatrix['validation']
	};
}

export function adaptFiiDiiFlow(value: unknown): FiiDiiFlowPoint {
	const row = asRecord(value);
	return {
		date: String(row['date'] ?? ''),
		fii: numberOrZero(row['fii']),
		dii: numberOrZero(row['dii']),
		net_flow: numberOrZero(row['net_flow']),
		fii_avg: maybeNumber(row['fii_avg']),
		dii_avg: maybeNumber(row['dii_avg']),
		net_flow_avg: maybeNumber(row['net_flow_avg'])
	};
}

export function adaptVixPoint(value: unknown) {
	const row = asRecord(value);
	return {
		date: String(row['date'] ?? ''),
		vix: numberOrZero(row['vix']),
		vix_change: maybeNumber(row['vix_change'])
	};
}
