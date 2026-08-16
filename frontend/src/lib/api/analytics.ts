import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';

import { adaptRegime, adaptRisk } from './adapters';
import { keys } from './query-keys';

export type RiskParams = {
	start_date?: string;
	end_date?: string;
	confidence_level?: number;
	risk_free_rate?: number;
	rolling_window?: number;
	persist?: boolean;
};

export function useRisk(id?: string, params: RiskParams = {}, enabled = true) {
	return useQuery({
		queryKey: keys.risk(id ?? 'none', params),
		queryFn: async () =>
			adaptRisk(
				await api.get<unknown>(`/analytics/portfolio/${id}/risk`, {
					confidence_level: params.confidence_level ?? 0.95,
					risk_free_rate: params.risk_free_rate ?? 0.06,
					rolling_window: params.rolling_window ?? 20,
					persist: params.persist ?? true,
					start_date: params.start_date,
					end_date: params.end_date
				})
			),
		enabled: Boolean(id) && enabled,
		retry: 0
	});
}

export type RegimeParams = {
	start_date?: string;
	end_date?: string;
	weights?: number[];
};

export function useRegime(id?: string, params: RegimeParams = {}, enabled = true) {
	return useQuery({
		queryKey: keys.regime(id ?? 'none', params),
		queryFn: () => {
			const body: Record<string, unknown> = {};
			if (params.start_date) body['start_date'] = params.start_date;
			if (params.end_date) body['end_date'] = params.end_date;
			if (params.weights && params.weights.length > 0) body['weights'] = params.weights;
			return api
				.post<unknown>(`/analytics/portfolio/${id}/regime`, body)
				.then((response) => adaptRegime(response));
		},
		enabled: Boolean(id) && enabled,
		retry: 0
	});
}
