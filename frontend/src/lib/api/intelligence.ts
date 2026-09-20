import { QueryClient, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api';
import type {
	IntelligenceRecommendation,
	MetricExplanation,
	PortfolioAlert,
	PortfolioIntelligence,
	RiskProfile,
	StressScenarioPreview,
	StressScenarioResult
} from '@/lib/types';

import { adaptRegime, adaptRisk } from './adapters';
import { keys } from './query-keys';
import { generateAIReport, listAIReports, type AIProvider } from './ai';

async function requestPortfolioIntelligence(
	queryClient: QueryClient,
	portfolioId: string,
	refresh = false
) {
	const data = await api.get<PortfolioIntelligence>(
		`/intelligence/portfolio/${portfolioId}`,
		refresh ? { refresh: true } : undefined
	);
	const normalized = {
		...data,
		risk: data.risk ? adaptRisk(data.risk) : data.risk,
		regime: data.regime ? adaptRegime(data.regime) : data.regime
	};
	queryClient.setQueryData(keys.intelligence(portfolioId), normalized);
	queryClient.setQueryData(keys.recommendations(portfolioId), normalized.recommendations);
	queryClient.setQueryData(keys.alerts(portfolioId), normalized.alerts);
	return normalized;
}

export function fetchPortfolioIntelligence(queryClient: QueryClient, portfolioId: string) {
	return queryClient.fetchQuery({
		queryKey: keys.intelligence(portfolioId),
		queryFn: () => requestPortfolioIntelligence(queryClient, portfolioId),
		staleTime: 60_000
	});
}

export function useIntelligence(portfolioId?: string) {
	const queryClient = useQueryClient();
	return useQuery({
		queryKey: keys.intelligence(portfolioId ?? 'none'),
		queryFn: () => requestPortfolioIntelligence(queryClient, portfolioId as string),
		enabled: Boolean(portfolioId),
		staleTime: 60_000
	});
}

export function useRefreshIntelligence(portfolioId?: string) {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: () => requestPortfolioIntelligence(queryClient, portfolioId as string, true)
	});
}

export function useRecommendations(portfolioId?: string) {
	const queryClient = useQueryClient();
	const query = useQuery({
		queryKey: keys.recommendations(portfolioId ?? 'none'),
		queryFn: async () => {
			const rows = await api.get<IntelligenceRecommendation[]>(
				`/intelligence/portfolio/${portfolioId}/recommendations`
			);
			const alerts = await api.get<PortfolioAlert[]>(
				`/intelligence/portfolio/${portfolioId}/alerts`
			);
			queryClient.setQueryData(keys.alerts(portfolioId ?? 'none'), alerts);
			return rows;
		},
		enabled: Boolean(portfolioId),
		staleTime: 60_000
	});
	const setRead = useMutation({
		mutationFn: ({ id, isRead }: { id: number; isRead: boolean }) =>
			api.patch<IntelligenceRecommendation>(
				`/intelligence/portfolio/${portfolioId}/recommendations/${id}`,
				{ is_read: isRead }
			),
		onSuccess: (updated) => {
			queryClient.setQueryData<IntelligenceRecommendation[]>(
				keys.recommendations(portfolioId ?? 'none'),
				(current = []) => current.map((item) => (item.id === updated.id ? updated : item))
			);
			queryClient.setQueryData<PortfolioIntelligence>(
				keys.intelligence(portfolioId ?? 'none'),
				(current) =>
					current
						? {
								...current,
								recommendations: current.recommendations.map((item) =>
									item.id === updated.id ? updated : item
								)
							}
						: current
			);
		}
	});
	return { ...query, setRead };
}

export function useAlerts(portfolioId?: string) {
	const queryClient = useQueryClient();
	const query = useQuery({
		queryKey: keys.alerts(portfolioId ?? 'none'),
		queryFn: () => api.get<PortfolioAlert[]>(`/intelligence/portfolio/${portfolioId}/alerts`),
		enabled: Boolean(portfolioId),
		staleTime: 60_000
	});
	const setRead = useMutation({
		mutationFn: ({ id, isRead }: { id: number; isRead: boolean }) =>
			api.patch<PortfolioAlert>(`/intelligence/portfolio/${portfolioId}/alerts/${id}`, {
				is_read: isRead
			}),
		onSuccess: (updated) => {
			queryClient.setQueryData<PortfolioAlert[]>(
				keys.alerts(portfolioId ?? 'none'),
				(current = []) => current.map((item) => (item.id === updated.id ? updated : item))
			);
			queryClient.setQueryData<PortfolioIntelligence>(
				keys.intelligence(portfolioId ?? 'none'),
				(current) =>
					current
						? {
								...current,
								alerts: current.alerts.map((item) => (item.id === updated.id ? updated : item))
							}
						: current
			);
		}
	});
	return { ...query, setRead };
}

export function useRiskProfile() {
	const queryClient = useQueryClient();
	const query = useQuery({
		queryKey: keys.riskProfile,
		queryFn: () => api.get<RiskProfile>('/intelligence/profile')
	});
	const update = useMutation({
		mutationFn: (payload: Omit<RiskProfile, 'id' | 'user_id' | 'created_at' | 'updated_at'>) =>
			api.put<RiskProfile>('/intelligence/profile', payload),
		onSuccess: async () => {
			await queryClient.invalidateQueries({ queryKey: keys.riskProfile });
			await queryClient.invalidateQueries({ queryKey: ['intelligence'] });
		}
	});
	return { ...query, update };
}

export function useMetricExplanation(
	portfolioId: string | undefined,
	metric: string,
	enabled: boolean
) {
	return useQuery({
		queryKey: keys.metricExplanation(portfolioId ?? 'none', metric),
		queryFn: () =>
			api.get<MetricExplanation>(`/intelligence/portfolio/${portfolioId}/explanations/${metric}`),
		enabled: Boolean(portfolioId) && enabled,
		staleTime: 60_000
	});
}

export function useStressScenario(portfolioId: string) {
	const parse = useMutation({
		mutationFn: (prompt: string) =>
			api.post<StressScenarioPreview>(`/intelligence/portfolio/${portfolioId}/stress/parse`, {
				prompt
			})
	});
	const run = useMutation({
		mutationFn: (payload: {
			name: string;
			description?: string;
			market_shock: number;
			volatility_shock: number;
			ticker_shocks: Record<string, number>;
			confirmed: boolean;
		}) =>
			api.post<StressScenarioResult>(`/intelligence/portfolio/${portfolioId}/stress/run`, payload)
	});
	return { parse, run };
}

export function useAIReports(portfolioId?: string) {
	const queryClient = useQueryClient();
	const query = useQuery({
		queryKey: keys.aiReports(portfolioId ?? 'none'),
		queryFn: () => listAIReports(portfolioId as string),
		enabled: Boolean(portfolioId)
	});
	const generate = useMutation({
		mutationFn: (payload: {
			reportType: string;
			provider: AIProvider;
			apiKey?: string;
			model?: string;
		}) => generateAIReport({ portfolioId: portfolioId as string, ...payload }),
		onSuccess: (report) => {
			queryClient.setQueryData(keys.aiReports(portfolioId ?? 'none'), (current: unknown) => [
				report,
				...(Array.isArray(current) ? current : [])
			]);
		}
	});
	return { ...query, generate };
}
