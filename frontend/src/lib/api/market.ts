import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';
import type { MarketSnapshot } from '@/lib/types';

import {
	adaptFeatureMatrix,
	adaptFiiDiiFlow,
	adaptHistoricalPrice,
	adaptLivePrice,
	adaptVixPoint,
	asArray,
	asRecord
} from './adapters';
import { keys } from './query-keys';

export type MarketParams = {
	tickers?: string[];
	start_date: string;
	end_date?: string;
	include_name?: boolean;
	window?: number;
	persist?: boolean;
	index_symbol?: string;
	include_features?: boolean;
	weights?: number[];
};

export function useMarketSnapshot(params: MarketParams, enabled = true) {
	return useQuery({
		queryKey: keys.market(params),
		queryFn: async (): Promise<MarketSnapshot> => {
			const tickers = params.tickers?.filter(Boolean) ?? [];
			const tickerParam = tickers.join(',');
			const commonParams = {
				start_date: params.start_date,
				end_date: params.end_date,
				persist: params.persist ?? true
			};
			const [historical, live, vix, flows, index, features] = await Promise.all([
				tickerParam
					? api.get<unknown>('/market/historical-prices', {
							tickers: tickerParam,
							...commonParams
						})
					: Promise.resolve(undefined),
				tickerParam
					? api.get<unknown>('/market/live-prices', {
							tickers: tickerParam,
							include_name: params.include_name ?? true
						})
					: Promise.resolve(undefined),
				api.get<unknown>('/market/india-vix', {
					...commonParams,
					window: params.window ?? 5
				}),
				api.get<unknown>('/market/fii-dii-flows', {
					start_date: params.start_date,
					end_date: params.end_date,
					window: params.window ?? 20,
					persist: params.persist ?? true
				}),
				api.get<unknown>('/market/index-data', {
					symbol: params.index_symbol ?? '^NSEI',
					...commonParams
				}),
				params.include_features && tickers.length > 0
					? api.post<unknown>(
							'/market/features/matrix',
							{
								tickers,
								start_date: params.start_date,
								end_date: params.end_date,
								weights: params.weights
							},
							{ persist: params.persist ?? true }
						)
					: Promise.resolve(undefined)
			]);
			return {
				historical_prices: asArray<unknown>(asRecord(historical)['prices']).map(
					adaptHistoricalPrice
				),
				live_prices: asArray<unknown>(asRecord(live)['prices']).map(adaptLivePrice),
				vix: asArray<unknown>(asRecord(vix)['points']).map(adaptVixPoint),
				fii_dii_flows: asArray<unknown>(asRecord(flows)['points']).map(adaptFiiDiiFlow),
				index_prices: asArray<unknown>(asRecord(index)['prices']).map(adaptHistoricalPrice),
				features: features ? adaptFeatureMatrix(features) : undefined
			};
		},
		enabled: enabled && Boolean(params.start_date),
		retry: 0
	});
}

export type HistoricalPriceParams = {
	tickers: string[];
	start_date: string;
	end_date?: string;
	persist?: boolean;
};

export function useHistoricalPrices(params: HistoricalPriceParams, enabled = true) {
	return useQuery({
		queryKey: keys.historicalPrices(params),
		queryFn: async () => {
			const response = await api.get<unknown>('/market/historical-prices', {
				tickers: params.tickers.join(','),
				start_date: params.start_date,
				end_date: params.end_date,
				persist: params.persist ?? true
			});
			return asArray<unknown>(asRecord(response)['prices']).map(adaptHistoricalPrice);
		},
		enabled: enabled && params.tickers.length > 0 && Boolean(params.start_date)
	});
}

export function useLivePrices(tickers: string[], enabled = true) {
	return useQuery({
		queryKey: keys.livePrices(tickers),
		queryFn: async () => {
			const response = await api.get<unknown>('/market/live-prices', {
				tickers: tickers.join(','),
				include_name: true
			});
			return asArray<unknown>(asRecord(response)['prices']).map(adaptLivePrice);
		},
		enabled: enabled && tickers.length > 0
	});
}
