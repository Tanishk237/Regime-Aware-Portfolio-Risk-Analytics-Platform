'use client';

import { ChartCard, SectionCard } from '@/components/charts/chart-card';
import { DataTable, type Column } from '@/components/common/data-table';
import { PnLValue, RegimeBadge, TradeTypeBadge } from '@/components/domain/finance';
import { MetricCard } from '@/components/common/metric-card';
import { SeriesLineChart } from '@/components/charts/series-charts';
import { EmptyState, LoadingSkeleton } from '@/components/common/states';
import { PageHeader } from '@/components/layout/top-bar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { buildHealthReport, buildRecommendations, metric } from '@/lib/analytics-derive';
import { formatCurrency, formatDate, formatNumber, formatPercent, toSeries } from '@/lib/format';
import {
	usePortfolio,
	usePositions,
	useRegime,
	useRisk,
	useSummary,
	useTrades
} from '@/lib/queries';
import type { Position, Trade } from '@/lib/types';
import { useParams } from 'next/navigation';

export default function PortfolioDetailPage() {
	const params = useParams<{ id: string }>();
	const portfolioId = params.id;
	const portfolio = usePortfolio(portfolioId);
	const summary = useSummary(portfolioId);
	const positions = usePositions(portfolioId);
	const trades = useTrades(portfolioId);
	const risk = useRisk(portfolioId);
	const regime = useRegime(portfolioId);

	const currency = portfolio.data?.base_currency ?? summary.data?.base_currency ?? 'INR';
	const cumulative = toSeries(risk.data?.series?.cumulative_returns);
	const health = buildHealthReport({
		summary: summary.data,
		positions: positions.data ?? [],
		risk: risk.data,
		regime: regime.data
	});
	const recommendations = buildRecommendations(health).slice(0, 3);

	const positionColumns: Array<Column<Position>> = [
		{
			key: 'ticker',
			header: 'Ticker',
			cell: (row) => <span className="font-medium">{row.ticker}</span>
		},
		{ key: 'qty', header: 'Qty', align: 'right', cell: (row) => formatNumber(row.quantity, 0) },
		{
			key: 'avg',
			header: 'Avg cost',
			align: 'right',
			cell: (row) => formatCurrency(row.average_cost, currency)
		},
		{
			key: 'price',
			header: 'Price',
			align: 'right',
			cell: (row) => formatCurrency(row.current_price, currency)
		},
		{
			key: 'mv',
			header: 'Market value',
			align: 'right',
			cell: (row) => formatCurrency(row.market_value, currency)
		},
		{
			key: 'pnl',
			header: 'Unrealized',
			align: 'right',
			cell: (row) => <PnLValue value={row.unrealized_pnl} currency={currency} />
		},
		{ key: 'w', header: 'Weight', align: 'right', cell: (row) => formatPercent(row.weight) }
	];

	const tradeColumns: Array<Column<Trade>> = [
		{ key: 'date', header: 'Date', cell: (row) => formatDate(row.transaction_date) },
		{
			key: 'ticker',
			header: 'Ticker',
			cell: (row) => <span className="font-medium">{row.ticker}</span>
		},
		{ key: 'type', header: 'Type', cell: (row) => <TradeTypeBadge type={row.transaction_type} /> },
		{ key: 'qty', header: 'Qty', align: 'right', cell: (row) => formatNumber(row.quantity, 0) },
		{
			key: 'price',
			header: 'Price',
			align: 'right',
			cell: (row) => formatCurrency(row.price, currency)
		},
		{ key: 'broker', header: 'Broker', cell: (row) => row.broker || '-' }
	];

	return (
		<div className="space-y-4">
			<PageHeader
				title={portfolio.data?.name ?? 'Portfolio'}
				description={`${currency} · Benchmark ${portfolio.data?.benchmark ?? '-'} · ${
					positions.data?.length ?? 0
				} positions · ${trades.data?.length ?? 0} trades`}
			/>

			<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
				<MetricCard
					label="Invested"
					value={formatCurrency(summary.data?.invested_value, currency)}
					loading={summary.isLoading}
				/>
				<MetricCard
					label="Current value"
					value={formatCurrency(summary.data?.current_value, currency)}
					loading={summary.isLoading}
				/>
				<MetricCard
					label="Total P&L"
					value={<PnLValue value={summary.data?.total_pnl} currency={currency} />}
					loading={summary.isLoading}
				/>
				<MetricCard label="Health score" value={`${health.score}/100`} hint={health.category} />
			</div>

			<Tabs defaultValue="overview">
				<TabsList>
					<TabsTrigger value="overview">Overview</TabsTrigger>
					<TabsTrigger value="positions">Positions</TabsTrigger>
					<TabsTrigger value="trades">Trades</TabsTrigger>
					<TabsTrigger value="analytics">Analytics</TabsTrigger>
				</TabsList>

				<TabsContent value="overview" className="mt-4 space-y-4">
					<ChartCard title="Cumulative returns">
						{cumulative.length === 0 ? (
							<EmptyState title="Portfolio returns are not available yet." />
						) : (
							<SeriesLineChart data={cumulative} />
						)}
					</ChartCard>
					<div className="grid gap-4 lg:grid-cols-2">
						<SectionCard
							title="Regime preview"
							action={<RegimeBadge label={regime.data?.current_regime} />}
						>
							<p className="text-muted-foreground text-sm">
								Confidence {formatPercent(regime.data?.confidence ?? regime.data?.probability)} ·
								state {regime.data?.current_state ?? '-'}
							</p>
						</SectionCard>
						<SectionCard title="Top recommendations">
							{recommendations.length === 0 ? (
								<EmptyState title="Run analytics to generate recommendations." />
							) : (
								<ul className="text-muted-foreground list-disc space-y-1 pl-5 text-sm">
									{recommendations.map((item) => (
										<li key={item.id}>{item.title}</li>
									))}
								</ul>
							)}
						</SectionCard>
					</div>
				</TabsContent>

				<TabsContent value="positions" className="mt-4">
					{positions.isLoading ? (
						<LoadingSkeleton />
					) : (
						<DataTable
							columns={positionColumns}
							rows={positions.data ?? []}
							rowKey={(row) => row.ticker}
							empty={<EmptyState title="This portfolio has no open positions." />}
						/>
					)}
				</TabsContent>

				<TabsContent value="trades" className="mt-4">
					{trades.isLoading ? (
						<LoadingSkeleton />
					) : (
						<DataTable
							columns={tradeColumns}
							rows={trades.data ?? []}
							rowKey={(row) => row.id}
							empty={
								<EmptyState title="Add trades manually or upload a CSV to calculate positions." />
							}
						/>
					)}
				</TabsContent>

				<TabsContent value="analytics" className="mt-4">
					<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
						<MetricCard label="CAGR" value={formatPercent(metric(risk.data, 'cagr'))} />
						<MetricCard
							label="Volatility"
							value={formatPercent(metric(risk.data, 'annualized_volatility'))}
						/>
						<MetricCard
							label="Max drawdown"
							value={formatPercent(metric(risk.data, 'max_drawdown'))}
						/>
						<MetricCard label="Sharpe" value={formatNumber(metric(risk.data, 'sharpe'), 2)} />
					</div>
				</TabsContent>
			</Tabs>
		</div>
	);
}
