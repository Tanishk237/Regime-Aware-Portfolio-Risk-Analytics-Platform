'use client';

import { useMemo } from 'react';

import { Skeleton } from '@/components/ui/skeleton';
import { formatNumber } from '@/lib/format';
import { useLivePrices, usePositions } from '@/lib/queries';
import { useSelectedPortfolio } from '@/lib/portfolio-context';
import { cn } from '@/lib/utils';

const MAX_LIVE_TICKERS = 20;
const MIN_TRACK_ITEMS = 8;

function displayTicker(ticker: string) {
	return ticker.replace(/\.NS$/i, '').replace(/\.BO$/i, '');
}

export function PortfolioMarketTape() {
	const { selectedId } = useSelectedPortfolio();
	const positions = usePositions(selectedId);
	const openPositions = useMemo(
		() =>
			(positions.data ?? [])
				.filter((position) => position.quantity > 0 && position.ticker)
				.sort((a, b) => (b.market_weight ?? b.weight ?? 0) - (a.market_weight ?? a.weight ?? 0)),
		[positions.data]
	);
	const tickers = useMemo(
		() => [...new Set(openPositions.map((position) => position.ticker))].slice(0, MAX_LIVE_TICKERS),
		[openPositions]
	);
	const livePrices = useLivePrices(tickers, Boolean(selectedId), 5 * 60_000);
	const rows = useMemo(() => {
		const liveByTicker = new Map((livePrices.data ?? []).map((price) => [price.ticker, price]));
		return tickers
			.map((ticker) => {
				const live = liveByTicker.get(ticker);
				const position = openPositions.find((item) => item.ticker === ticker);
				const price = live?.price ?? position?.current_price ?? 0;
				return {
					ticker,
					price,
					isStale: live?.is_stale ?? !live,
					asOf: live?.as_of ?? position?.updated_at ?? ''
				};
			})
			.filter((item) => Number.isFinite(item.price) && item.price > 0);
	}, [livePrices.data, openPositions, tickers]);

	const trackRows = useMemo(() => {
		if (!rows.length) return [];
		const sequence = [...rows];
		while (sequence.length < MIN_TRACK_ITEMS) sequence.push(...rows);
		return [...sequence, ...sequence];
	}, [rows]);

	if (!selectedId) return null;
	if (positions.isLoading && !positions.data) {
		return (
			<div className="border-border/70 bg-card/65 flex h-9 items-center gap-3 border-b px-4">
				<Skeleton className="h-2 w-24" />
				<Skeleton className="h-2 w-32" />
				<Skeleton className="h-2 w-28" />
			</div>
		);
	}
	if (!trackRows.length) return null;

	return (
		<section
			aria-label="Selected portfolio market prices"
			className="border-border/70 bg-card/72 group sticky top-16 z-20 flex h-9 min-w-0 items-center overflow-hidden border-b backdrop-blur-xl"
		>
			<div className="border-border/70 bg-card/95 z-10 hidden h-full shrink-0 items-center gap-2 border-r px-3 text-xs font-medium sm:flex">
				<span className="bg-positive relative size-1.5 rounded-full">
					<span className="bg-positive absolute inset-0 rounded-full opacity-40 motion-safe:animate-ping" />
				</span>
				Portfolio prices
			</div>
			<div className="min-w-0 flex-1 overflow-hidden">
				<div className="market-tape-track flex w-max items-center gap-7 px-4">
					{trackRows.map((item, index) => (
						<div
							key={`${item.ticker}-${index}`}
							className="flex h-9 items-center gap-2 whitespace-nowrap text-xs"
							title={`${item.ticker}${item.asOf ? ` · ${item.asOf}` : ''}${item.isStale ? ' · latest stored price' : ''}`}
						>
							<span
								className={cn('size-1.5 rounded-full', item.isStale ? 'bg-warning' : 'bg-primary')}
								aria-hidden
							/>
							<span className="text-foreground/90 font-medium">{displayTicker(item.ticker)}</span>
							<span className="text-muted-foreground tabular-nums">
								{formatNumber(item.price, 2)}
							</span>
							{item.isStale ? (
								<span className="text-warning hidden text-[10px] sm:inline">stored</span>
							) : null}
						</div>
					))}
				</div>
			</div>
		</section>
	);
}
