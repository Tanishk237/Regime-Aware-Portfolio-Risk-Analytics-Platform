import { createContext, useContext, useEffect, useMemo, useState } from 'react';

import { usePortfolios } from '@/lib/queries';
import type { Portfolio } from '@/lib/types';

const STORAGE_KEY = 'rapra.selectedPortfolio';

type PortfolioContextValue = {
	portfolios: Portfolio[];
	isLoading: boolean;
	error: unknown;
	selectedId: string | undefined;
	selected: Portfolio | undefined;
	select: (id: string) => void;
	refetch: () => void;
};

const PortfolioContext = createContext<PortfolioContextValue | null>(null);

export function SelectedPortfolioProvider({ children }: { children: React.ReactNode }) {
	const { data, isLoading, error, refetch } = usePortfolios();
	const portfolios = useMemo(() => data ?? [], [data]);
	const [selectedId, setSelectedId] = useState<string | undefined>(undefined);

	useEffect(() => {
		if (portfolios.length === 0) return;
		setSelectedId((current) => {
			if (current && portfolios.some((p) => p.id === current)) return current;
			const stored =
				typeof window === 'undefined' ? null : window.localStorage.getItem(STORAGE_KEY);
			if (stored && portfolios.some((p) => p.id === stored)) return stored;
			return portfolios[0]?.id;
		});
	}, [portfolios]);

	const value = useMemo<PortfolioContextValue>(
		() => ({
			portfolios,
			isLoading,
			error,
			selectedId,
			selected: portfolios.find((p) => p.id === selectedId),
			select: (id: string) => {
				window.localStorage.setItem(STORAGE_KEY, id);
				setSelectedId(id);
			},
			refetch: () => void refetch()
		}),
		[portfolios, isLoading, error, selectedId, refetch]
	);

	return <PortfolioContext.Provider value={value}>{children}</PortfolioContext.Provider>;
}

export function useSelectedPortfolio() {
	const ctx = useContext(PortfolioContext);
	if (!ctx) throw new Error('useSelectedPortfolio must be used inside SelectedPortfolioProvider');
	return ctx;
}
