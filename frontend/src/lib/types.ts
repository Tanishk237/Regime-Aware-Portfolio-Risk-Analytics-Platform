export type Portfolio = {
	id: string;
	user_id?: string;
	name: string;
	description?: string | null;
	base_currency?: string | null;
	benchmark?: string | null;
	created_at?: string | null;
	updated_at?: string | null;
};

export type Trade = {
	id: string;
	portfolio_id?: string;
	ticker: string;
	transaction_type: 'BUY' | 'SELL';
	quantity: number;
	price: number;
	transaction_date: string;
	broker?: string | null;
	fees?: number | null;
	taxes?: number | null;
	currency?: string | null;
	notes?: string | null;
};

export type TradeInput = Omit<Trade, 'id' | 'portfolio_id'>;

export type Position = {
	id?: string;
	portfolio_id?: string;
	ticker: string;
	quantity: number;
	average_cost?: number | null;
	avg_cost?: number | null;
	current_price?: number | null;
	market_value?: number | null;
	cost_basis?: number | null;
	unrealized_pnl?: number | null;
	realized_pnl?: number | null;
	weight?: number | null;
	market_weight?: number | null;
	cost_weight?: number | null;
	updated_at?: string | null;
};

export type PortfolioSummary = {
	portfolio_id?: string;
	name?: string;
	base_currency?: string;
	benchmark?: string;
	invested_value?: number;
	current_value?: number;
	total_pnl?: number;
	unrealized_pnl?: number;
	realized_pnl?: number;
	latest_return?: number;
	total_return?: number;
	position_count?: number;
	trade_count?: number;
	positions_count?: number;
	trades_count?: number;
	as_of?: string;
};

export type SeriesPoint = { date: string; value: number };

export type RiskAnalytics = {
	success?: boolean;
	portfolio_id?: string;
	as_of?: string;
	returns?: SeriesPoint[];
	metrics?: Record<string, number | null>;
	pnl?: {
		total_cost_basis?: number;
		cost_basis?: number;
		market_value?: number;
		realized_pnl?: number;
		unrealized_pnl?: number;
		total_pnl?: number;
		positions?: Position[];
	};
	series?: {
		daily_returns?: Record<string, number> | SeriesPoint[];
		cumulative_returns?: Record<string, number> | SeriesPoint[];
		drawdown?: Record<string, number> | SeriesPoint[];
		rolling_returns?: Record<string, number> | SeriesPoint[];
		rolling_volatility?: Record<string, number> | SeriesPoint[];
	};
	parameters?: Record<string, unknown>;
	generated_at?: string;
};

export type RegimeHistoryRow = {
	date: string;
	hidden_state: number;
	label?: string;
	regime_label?: string;
	probability?: number;
};

export type RegimeAnalytics = {
	success?: boolean;
	portfolio_id?: string;
	tickers?: string[];
	current_regime?: string;
	current_state?: number;
	confidence?: number;
	probability?: number;
	regime_probability?: number;
	regime_switches?: number;
	current_duration_days?: number;
	transition_matrix?: number[][];
	state_labels?: Record<string, string>;
	feature_metadata?: Record<string, unknown>;
	history?: RegimeHistoryRow[];
	regime_history?: RegimeHistoryRow[];
	statistics?: Array<{
		hidden_state: number;
		label?: string;
		regime_label?: string;
		sample_count?: number;
		avg_return?: number;
		average_return?: number | null;
		avg_volatility?: number;
		average_volatility?: number | null;
		avg_drawdown?: number;
		average_drawdown?: number | null;
		avg_vix?: number;
		average_vix?: number | null;
	}>;
	regime_statistics?: RegimeAnalytics['statistics'];
	durations?: Array<{
		hidden_state: number;
		label?: string;
		start_date: string;
		end_date: string;
		duration_days: number;
	}>;
	regime_duration?: RegimeAnalytics['durations'];
	fallback_used?: boolean;
	generated_at?: string;
};

export type PortfolioReturn = {
	id?: string;
	portfolio_id?: string;
	date: string;
	daily_return: number;
	cumulative_return?: number | null;
	portfolio_value?: number | null;
	created_at?: string | null;
};

export type HistoricalPricePoint = {
	ticker: string;
	date: string;
	open?: number | null;
	high?: number | null;
	low?: number | null;
	close: number;
	volume?: number | null;
};

export type LivePricePoint = {
	ticker: string;
	price: number;
	name?: string | null;
};

export type VixPoint = {
	date: string;
	vix: number;
	vix_change?: number | null;
};

export type FiiDiiFlowPoint = {
	date: string;
	fii: number;
	dii: number;
	net_flow: number;
	fii_avg?: number | null;
	dii_avg?: number | null;
	net_flow_avg?: number | null;
};

export type FeatureMatrixRecord = {
	date: string;
	values: Record<string, number>;
};

export type FeatureValidationReport = {
	is_valid: boolean;
	rows: number;
	columns: number;
	missing_values: number;
	duplicate_index: number;
	infinite_values: number;
	feature_names: string[];
};

export type FeatureMatrix = {
	tickers: string[];
	start_date: string;
	end_date?: string | null;
	columns: string[];
	records: FeatureMatrixRecord[];
	metadata: Record<string, unknown>;
	validation: FeatureValidationReport;
};

export type MarketSnapshot = {
	historical_prices: HistoricalPricePoint[];
	live_prices: LivePricePoint[];
	vix: VixPoint[];
	fii_dii_flows: FiiDiiFlowPoint[];
	index_prices: HistoricalPricePoint[];
	features?: FeatureMatrix;
};

export type HealthStatus = {
	status?: string;
	database?: string;
	[key: string]: unknown;
};

export type VersionInfo = {
	version?: string;
	environment?: string;
	[key: string]: unknown;
};
