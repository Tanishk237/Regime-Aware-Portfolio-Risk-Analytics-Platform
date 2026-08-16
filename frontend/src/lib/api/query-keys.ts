export const keys = {
	health: ['health'] as const,
	version: ['version'] as const,
	portfolios: ['portfolios'] as const,
	portfolio: (id: string) => ['portfolio', id] as const,
	summary: (id: string) => ['portfolio', id, 'summary'] as const,
	positions: (id: string) => ['portfolio', id, 'positions'] as const,
	trades: (id: string) => ['portfolio', id, 'trades'] as const,
	returns: (id: string) => ['portfolio', id, 'returns'] as const,
	risk: (id: string, params: unknown) => ['risk', id, params] as const,
	regime: (id: string, params: unknown) => ['regime', id, params] as const,
	market: (params: unknown) => ['market', params] as const,
	historicalPrices: (params: unknown) => ['historical-prices', params] as const,
	livePrices: (tickers: string[]) => ['live-prices', tickers] as const
};
