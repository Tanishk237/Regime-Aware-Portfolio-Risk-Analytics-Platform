export type Portfolio = {
	id: string;
	user_id?: string;
	name: string;
	description?: string | null;
	base_currency?: string | null;
	benchmark?: string | null;
	is_demo?: boolean;
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
	name?: string | null;
	sector?: string | null;
	industry?: string | null;
};

export type SectorAllocation = {
	sector: string;
	market_value: number;
	weight: number;
	holdings_count: number;
	tickers: string[];
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
	return_pct?: number;
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
	explanation?: {
		summary: string;
		drivers: string[];
		current_duration_days: number;
		likely_next_state?: string | null;
		likely_next_probability?: number | null;
		model_mode: string;
		probability_note: string;
	};
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

export type Citation = {
	label: string;
	value: string;
	source: string;
	as_of?: string | null;
};

export type RiskProfile = {
	id: number;
	user_id: number;
	tolerance: 'conservative' | 'moderate' | 'aggressive';
	horizon_months: number;
	max_drawdown_tolerance: number;
	liquidity_needs: 'low' | 'medium' | 'high';
	income_requirement?: string | null;
	restrictions: string[];
	created_at: string;
	updated_at: string;
};

export type PortfolioIntelligence = {
	portfolio_id: number;
	data_as_of?: string | null;
	summary: PortfolioSummary;
	positions: Position[];
	sector_allocation: SectorAllocation[];
	risk?: RiskAnalytics | null;
	regime?: RegimeAnalytics | null;
	risk_profile: RiskProfile;
	executive_summary: string[];
	citations: Citation[];
	warnings: string[];
	recommendations: IntelligenceRecommendation[];
	alerts: PortfolioAlert[];
};

export type MetricExplanation = {
	metric: string;
	title: string;
	definition: string;
	value: string;
	interpretation: string;
	why_it_matters: string;
	source: string;
	data_as_of?: string | null;
	ask_prompt: string;
};

export type IntelligenceRecommendation = {
	id: number;
	fingerprint: string;
	severity: 'high' | 'medium' | 'low';
	category: string;
	title: string;
	description: string;
	evidence: string;
	action: string;
	expected_impact: string;
	confidence: number;
	is_read: boolean;
	created_at: string;
};

export type PortfolioAlert = {
	id: number;
	alert_type: string;
	severity: 'high' | 'medium' | 'low';
	title: string;
	description: string;
	evidence?: string | null;
	is_read: boolean;
	detected_at: string;
};

export type StressScenarioPreview = {
	name: string;
	prompt: string;
	market_shock: number;
	volatility_shock: number;
	ticker_shocks: Record<string, number>;
	assumptions: string[];
	requires_confirmation: boolean;
};

export type StressScenarioResult = {
	id: number;
	name: string;
	description?: string | null;
	value_before: number;
	value_after: number;
	estimated_impact: number;
	estimated_impact_pct: number;
	historical_var_before?: number | null;
	historical_var_after?: number | null;
	position_impacts: Array<{
		ticker: string;
		applied_shock: number;
		value_before: number;
		value_after: number;
		impact: number;
	}>;
	assumptions: string[];
	generated_at: string;
};

export type AIReport = {
	id: number;
	portfolio_id: number;
	report_type: string;
	title: string;
	content: string;
	provider?: string | null;
	model?: string | null;
	response_mode: 'provider' | 'local' | 'local_fallback';
	data_as_of?: string | null;
	created_at: string;
};

export type CsvValidationIssue = {
	row?: number | null;
	field?: string | null;
	message: string;
};

export type CsvPreview = {
	valid: boolean;
	total_rows: number;
	valid_rows: number;
	duplicate_rows: number;
	detected_columns: string[];
	normalized_columns: string[];
	column_mapping: Record<string, string>;
	missing_columns: string[];
	unknown_columns: string[];
	warnings: CsvValidationIssue[];
	errors: CsvValidationIssue[];
	preview: Array<Record<string, unknown>>;
};

export type CsvResolutionChange = {
	row?: number | null;
	field: string;
	before?: unknown;
	after?: unknown;
	reason: string;
};

export type CsvResolution = {
	resolved_csv: string;
	changes: CsvResolutionChange[];
	report: CsvPreview;
};
