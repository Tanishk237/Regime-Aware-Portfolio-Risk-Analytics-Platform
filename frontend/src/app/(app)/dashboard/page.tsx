'use client';

import Link from 'next/link';

import { ChartCard, SectionCard } from '@/components/charts/chart-card';
import { DataTable, type Column } from '@/components/common/data-table';
import { MetricCard } from '@/components/common/metric-card';
import { NoTradesState, RequirePortfolio } from '@/components/layout/require-portfolio';
import { EmptyState, ErrorState, MetricGridSkeleton } from '@/components/common/states';
import { SeriesAreaChart, SeriesLineChart } from '@/components/charts/series-charts';
import { CategoryBadge, SeverityBadge } from '@/components/domain/finance';
import { PageHeader } from '@/components/layout/top-bar';
import { Button } from '@/components/ui/button';
import { buildHealthReport, buildRecommendations, metric } from '@/lib/analytics-derive';
import { formatCurrency, formatNumber, formatPercent, toSeries } from '@/lib/format';
import { useSelectedPortfolio } from '@/lib/portfolio-context';
import { usePositions, useRegime, useRisk, useSummary, useTrades } from '@/lib/queries';
import type { Position } from '@/lib/types';

export default function DashboardPage() {
	return (
		<RequirePortfolio label="the dashboard">
			{(id) => <Dashboard portfolioId={id} />}
		</RequirePortfolio>
	);
}

function Dashboard({ portfolioId }: { portfolioId: string }) {
	const { selected } = useSelectedPortfolio();
	const summary = useSummary(portfolioId);
	const positions = usePositions(portfolioId);
	const trades = useTrades(portfolioId);
	const risk = useRisk(portfolioId);
	const regime = useRegime(portfolioId);
	const currency = selected?.base_currency ?? summary.data?.base_currency ?? 'INR';
	const health = buildHealthReport({
		summary: summary.data,
		positions: positions.data ?? [],
		risk: risk.data,
		regime: regime.data
	});
	const recommendations = buildRecommendations(health).slice(0, 3);
	const cumulative = toSeries(risk.data?.series?.cumulative_returns);
	const drawdown = toSeries(risk.data?.series?.drawdown);
	const positionColumns: Array<Column<Position>> = [
		{
			key: 'ticker',
			header: 'Ticker',
			cell: (row) => <span className="font-medium">{row.ticker}</span>
		},
		{
			key: 'quantity',
			header: 'Qty',
			align: 'right',
			cell: (row) => <span className="num">{formatNumber(row.quantity, 0)}</span>
		},
		{
			key: 'weight',
			header: 'Weight',
			align: 'right',
			cell: (row) => <span className="num">{formatPercent(row.weight ?? row.market_weight)}</span>
		},
		{
			key: 'value',
			header: 'Value',
			align: 'right',
			cell: (row) => (
				<span className="num">{formatCurrency(row.market_value ?? row.cost_basis, currency)}</span>
			)
		}
	];
	const topPositions = [...(positions.data ?? [])]
		.sort((a, b) => (b.weight ?? b.market_weight ?? 0) - (a.weight ?? a.market_weight ?? 0))
		.slice(0, 6);

	return (
		<div className="space-y-4">
			<PageHeader
				title={selected?.name ?? 'Dashboard'}
				description="Portfolio overview, P&L, risk analytics, and current market regime."
			/>
			{!trades.isLoading && (trades.data?.length ?? 0) === 0 ? <NoTradesState /> : null}
			{summary.isLoading ? (
				<MetricGridSkeleton count={8} />
			) : summary.isError ? (
				<ErrorState error={summary.error} onRetry={() => void summary.refetch()} />
			) : (
				<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
					<MetricCard
						label="Invested value"
						value={formatCurrency(summary.data?.invested_value, currency)}
					/>
					<MetricCard
						label="Current value"
						value={formatCurrency(summary.data?.current_value, currency)}
					/>
					<MetricCard
						label="Total return"
						value={formatPercent(summary.data?.total_return ?? metric(risk.data, 'total_return'))}
					/>
					<MetricCard
						label="Current regime"
						value={regime.data?.current_regime ?? '—'}
						loading={regime.isLoading}
					/>
					<MetricCard
						label="Regime confidence"
						value={formatPercent(regime.data?.confidence ?? regime.data?.probability)}
						loading={regime.isLoading}
					/>
					<MetricCard label="Health score" value={`${health.score}/100`} hint={health.category} />
					<MetricCard
						label="Open positions"
						value={positions.data?.length ?? 0}
						loading={positions.isLoading}
					/>
					<MetricCard label="Trades" value={trades.data?.length ?? 0} loading={trades.isLoading} />
				</div>
			)}
			<SectionCard title="Workflow">
				<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
					<Button asChild variant="outline">
						<Link href="/portfolios">Manage portfolios</Link>
					</Button>
					<Button asChild variant="outline">
						<Link href="/trades">Add trades</Link>
					</Button>
					<Button asChild variant="outline">
						<Link href="/risk">Run risk</Link>
					</Button>
					<Button asChild variant="outline">
						<Link href="/regime">Run regime</Link>
					</Button>
					<Button asChild variant="outline">
						<Link href="/stress-tests">Stress test</Link>
					</Button>
				</div>
			</SectionCard>

			<div className="grid gap-4 lg:grid-cols-2">
				<ChartCard title="Cumulative returns">
					{risk.isLoading ? (
						<MetricGridSkeleton count={2} />
					) : cumulative.length ? (
						<SeriesLineChart data={cumulative} />
					) : (
						<EmptyState title="No return series available" />
					)}
				</ChartCard>
				<ChartCard title="Drawdown">
					{risk.isLoading ? (
						<MetricGridSkeleton count={2} />
					) : drawdown.length ? (
						<SeriesAreaChart data={drawdown} />
					) : (
						<EmptyState title="No drawdown series available" />
					)}
				</ChartCard>
			</div>

			<div className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(20rem,0.7fr)]">
				<SectionCard title="Top positions">
					{positions.isLoading ? (
						<MetricGridSkeleton count={2} />
					) : topPositions.length ? (
						<DataTable
							dense
							columns={positionColumns}
							rows={topPositions}
							rowKey={(row) => row.id ?? row.ticker}
						/>
					) : (
						<EmptyState title="No positions available" />
					)}
				</SectionCard>
				<SectionCard title="Top recommendations">
					{recommendations.length ? (
						<div className="space-y-3">
							{recommendations.map((item) => (
								<div key={item.id} className="rounded-lg border p-3">
									<div className="flex flex-wrap gap-2">
										<SeverityBadge severity={item.severity} />
										<CategoryBadge category={item.category} />
									</div>
									<p className="mt-2 text-sm font-medium">{item.title}</p>
									<p className="text-muted-foreground mt-1 text-xs">{item.action}</p>
								</div>
							))}
							<Button asChild size="sm" variant="outline">
								<Link href="/recommendations">View all recommendations</Link>
							</Button>
						</div>
					) : (
						<EmptyState title="No active recommendations" />
					)}
				</SectionCard>
			</div>
		</div>
	);
}
