import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api';
import type { Portfolio, TradeInput } from '@/lib/types';

import {
	adaptPortfolio,
	adaptPortfolioReturn,
	adaptPosition,
	adaptSummary,
	adaptTrade,
	asArray
} from './adapters';
import { keys } from './query-keys';

export function usePortfolios() {
	return useQuery({
		queryKey: keys.portfolios,
		queryFn: async () => asArray<unknown>(await api.get<unknown>('/portfolio')).map(adaptPortfolio)
	});
}

export function usePortfolio(id?: string) {
	return useQuery({
		queryKey: keys.portfolio(id ?? 'none'),
		queryFn: async () => adaptPortfolio(await api.get<unknown>(`/portfolio/${id}`)),
		enabled: Boolean(id)
	});
}

export function useSummary(id?: string) {
	return useQuery({
		queryKey: keys.summary(id ?? 'none'),
		queryFn: async () => adaptSummary(await api.get<unknown>(`/portfolio/${id}/summary`)),
		enabled: Boolean(id)
	});
}

export function usePositions(id?: string) {
	return useQuery({
		queryKey: keys.positions(id ?? 'none'),
		queryFn: async () =>
			asArray<unknown>(await api.get<unknown>(`/portfolio/${id}/positions`)).map(adaptPosition),
		enabled: Boolean(id)
	});
}

export function useTrades(id?: string) {
	return useQuery({
		queryKey: keys.trades(id ?? 'none'),
		queryFn: async () =>
			asArray<unknown>(await api.get<unknown>(`/portfolio/${id}/trades`)).map(adaptTrade),
		enabled: Boolean(id)
	});
}

export function useReturns(id?: string) {
	return useQuery({
		queryKey: keys.returns(id ?? 'none'),
		queryFn: async () =>
			asArray<unknown>(await api.get<unknown>(`/portfolio/${id}/returns`)).map(
				adaptPortfolioReturn
			),
		enabled: Boolean(id)
	});
}

export function usePortfolioMutations() {
	const queryClient = useQueryClient();
	const invalidate = () => queryClient.invalidateQueries({ queryKey: keys.portfolios });

	const create = useMutation({
		mutationFn: async (input: Partial<Portfolio>) =>
			adaptPortfolio(await api.post<unknown>('/portfolio', input)),
		onSuccess: invalidate
	});

	const update = useMutation({
		mutationFn: ({ id, ...input }: Partial<Portfolio> & { id: string }) =>
			api.put<unknown>(`/portfolio/${id}`, input).then(adaptPortfolio),
		onSuccess: (_data, variables) => {
			invalidate();
			queryClient.invalidateQueries({ queryKey: keys.portfolio(variables.id) });
		}
	});

	const remove = useMutation({
		mutationFn: (id: string) => api.del<unknown>(`/portfolio/${id}`),
		onSuccess: invalidate
	});

	return { create, update, remove };
}

export function useTradeMutations(portfolioId?: string) {
	const queryClient = useQueryClient();
	const invalidate = () => {
		if (!portfolioId) return;
		queryClient.invalidateQueries({ queryKey: keys.trades(portfolioId) });
		queryClient.invalidateQueries({ queryKey: keys.positions(portfolioId) });
		queryClient.invalidateQueries({ queryKey: keys.summary(portfolioId) });
		queryClient.invalidateQueries({ queryKey: ['risk', portfolioId] });
		queryClient.invalidateQueries({ queryKey: ['regime', portfolioId] });
	};

	const create = useMutation({
		mutationFn: (input: TradeInput) =>
			api.post<unknown>(`/portfolio/${portfolioId}/trades`, input).then(adaptTrade),
		onSuccess: invalidate
	});

	const update = useMutation({
		mutationFn: ({ id, ...input }: TradeInput & { id: string }) =>
			api.put<unknown>(`/portfolio/${portfolioId}/trades/${id}`, input).then(adaptTrade),
		onSuccess: invalidate
	});

	const remove = useMutation({
		mutationFn: (id: string) => api.del<unknown>(`/portfolio/${portfolioId}/trades/${id}`),
		onSuccess: invalidate
	});

	return { create, update, remove };
}

export function useCsvUpload() {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: (formData: FormData) =>
			api.upload<Record<string, unknown>>('/portfolio/upload', formData),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.portfolios })
	});
}
