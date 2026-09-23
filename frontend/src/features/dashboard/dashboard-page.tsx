'use client';

import {
	Activity,
	ArrowRight,
	Bot,
	HeartPulse,
	LineChart,
	ReceiptText,
	ShieldCheck,
	Upload
} from 'lucide-react';
import Link from 'next/link';

import { ChartCard, SectionCard } from '@/components/charts/chart-card';
import { SectorAllocationChart } from '@/components/charts/sector-allocation-chart';
import { SeriesAreaChart, SeriesLineChart } from '@/components/charts/series-charts';
import { DataTable, type Column } from '@/components/common/data-table';
import { MetricCard } from '@/components/common/metric-card';
import { EmptyState, ErrorState, MetricGridSkeleton } from '@/components/common/states';
import { CategoryBadge, PnLValue, RegimeBadge, SeverityBadge } from '@/components/domain/finance';
import { NoTradesState, RequirePortfolio } from '@/components/layout/require-portfolio';
import { PageHeader } from '@/components/layout/top-bar';
import { Reveal } from '@/components/motion/reveal';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { buildHealthReport, metric } from '@/lib/analytics-derive';
import { formatCurrency, formatDate, formatNumber, formatPercent, toSeries } from '@/lib/format';
import { useSelectedPortfolio } from '@/lib/portfolio-context';
import { useIntelligence, usePositions, useReturns, useSummary, useTrades } from '@/lib/queries';
import { cumulativeSeriesFromReturns, drawdownSeriesFromCumulative } from '@/lib/series';
import type { Position } from '@/lib/types';
import { cn } from '@/lib/utils';

import { DashboardGuide } from './dashboard-guide';
import { PortfolioSignal, RegimeStateRail } from './dashboard-signals';

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
	const returns = useReturns(portfolioId);
	const intelligence = useIntelligence(portfolioId);
	const riskData = intelligence.data?.risk ?? undefined;
	const regimeData = intelligence.data?.regime ?? undefined;
	const currency = selected?.base_currency ?? summary.data?.base_currency ?? 'INR';
	const health = buildHealthReport({
		summary: summary.data,
		positions: positions.data ?? [],
		risk: riskData,
		regime: regimeData
	});
	const recommendations = (intelligence.data?.recommendations ?? []).slice(0, 3);
	const sectorAllocation = intelligence.data?.sector_allocation ?? [];
	const persistedCumulative = cumulativeSeriesFromReturns(returns.data);
	const cumulative = toSeries(riskData?.series?.cumulative_returns);
	const chartCumulative = cumulative.length ? cumulative : persistedCumulative;
	const drawdown = toSeries(riskData?.series?.drawdown);
	const chartDrawdown = drawdown.length ? drawdown : drawdownSeriesFromCumulative(chartCumulative);
	const periodReturn = chartCumulative.at(-1)?.value;
	const worstDrawdown = chartDrawdown.length
		? Math.min(...chartDrawdown.map((point) => point.value))
		: undefined;
	const chartsLoading = intelligence.isLoading && returns.isLoading;
	const totalReturn = summary.data?.total_return;
	const regimeConfidence =
		regimeData?.regime_probability ?? regimeData?.confidence ?? regimeData?.probability;
	const maxDrawdown = metric(riskData, 'max_drawdown');
	const annualizedVolatility = metric(riskData, 'annualized_volatility');
	const historicalVar = metric(riskData, 'historical_var');
	const dataAsOf = intelligence.data?.data_as_of ?? riskData?.as_of;
	const openPositions = (positions.data ?? []).filter((position) => position.quantity > 0);
	const topPositions = [...openPositions]
		.sort((a, b) => (b.weight ?? b.market_weight ?? 0) - (a.weight ?? a.market_weight ?? 0))
		.slice(0, 6);
	const returnTone =
		(totalReturn ?? 0) > 0
			? 'text-positive'
			: (totalReturn ?? 0) < 0
				? 'text-negative'
				: 'text-foreground';

	const positionColumns: Array<Column<Position>> = [
		{
			key: 'ticker',
			header: 'Holding',
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
			header: 'Market value',
			align: 'right',
			cell: (row) => (
				<span className="num">{formatCurrency(row.market_value ?? row.cost_basis, currency)}</span>
			)
		}
	];

	return (
		<div className="space-y-5">
			<PageHeader
				title={selected?.name ?? 'Portfolio dashboard'}
				description={
					dataAsOf
						? `Decision snapshot using market data through ${formatDate(dataAsOf)}.`
						: 'A connected view of performance, market regime, risk, and next actions.'
				}
				actions={
					<>
						<DashboardGuide portfolioId={portfolioId} />
						<Button asChild size="sm" variant="outline">
							<Link href="/upload">
								<Upload className="size-4" /> Upload CSV
							</Link>
						</Button>
						<Button asChild size="sm">
							<Link href="/ai-copilot">
								<Bot className="size-4" /> Ask Copilot
							</Link>
						</Button>
					</>
				}
			/>

			{!trades.isLoading && (trades.data?.length ?? 0) === 0 ? <NoTradesState /> : null}
			{summary.isError ? (
				<ErrorState error={summary.error} onRetry={() => void summary.refetch()} />
			) : null}
			{intelligence.data?.executive_summary.length ? (
				<Reveal>
					<SectionCard
						title="Latent portfolio reading"
						description="A concise interpretation assembled from the same backend values used below."
						action={
							<Button asChild size="sm" variant="ghost">
								<Link href="/ai-copilot">
									Ask a follow-up <ArrowRight className="size-3.5" />
								</Link>
							</Button>
						}
					>
						<div className="divide-border grid divide-y lg:grid-cols-3 lg:divide-x lg:divide-y-0">
							{intelligence.data.executive_summary.slice(0, 3).map((item, index) => (
								<div
									key={item}
									className="flex gap-3 py-3 text-sm leading-6 first:pt-0 last:pb-0 lg:px-4 lg:py-0 lg:first:pl-0 lg:last:pr-0"
								>
									<span className="num text-primary/80 pt-0.5 text-xs font-semibold">
										0{index + 1}
									</span>
									<span>{item}</span>
								</div>
							))}
						</div>
						{intelligence.data.warnings.length ? (
							<p className="text-warning mt-3 text-xs">{intelligence.data.warnings.join(' ')}</p>
						) : null}
					</SectionCard>
				</Reveal>
			) : null}

			{summary.isLoading ? (
				<MetricGridSkeleton count={6} />
			) : (
				<Reveal className="grid gap-4 lg:grid-cols-5">
					<Card className="panel-surface signal-surface relative min-h-[19rem] overflow-hidden p-5 sm:p-6 lg:col-span-3">
						<div className="flex flex-wrap items-start justify-between gap-4">
							<div>
								<p className="text-muted-foreground text-xs font-medium uppercase">
									Portfolio value
								</p>
								<p className="num mt-2 text-3xl font-semibold sm:text-4xl">
									{formatCurrency(summary.data?.current_value, currency)}
								</p>
								<div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
									<PnLValue
										value={summary.data?.total_pnl}
										currency={currency}
										className="font-medium"
									/>
									<span className="text-muted-foreground">total P&amp;L</span>
								</div>
							</div>
							<div className={cn('text-right', returnTone)}>
								<p className="text-muted-foreground text-xs font-medium uppercase">Total return</p>
								<p className="num mt-2 text-2xl font-semibold">{formatPercent(totalReturn)}</p>
							</div>
						</div>
						<PortfolioSignal data={chartCumulative} />
						<Separator className="mb-5 mt-1" />
						<div className="grid gap-3 text-sm sm:grid-cols-3">
							<DashboardDatum
								label="Invested capital"
								value={formatCurrency(summary.data?.invested_value, currency)}
							/>
							<DashboardDatum
								label="Open positions"
								value={formatNumber(openPositions.length, 0)}
							/>
							<DashboardDatum
								label="Recorded trades"
								value={formatNumber(trades.data?.length, 0)}
							/>
						</div>
					</Card>

					<Card className="panel-surface signal-surface relative min-h-[19rem] overflow-hidden p-5 sm:p-6 lg:col-span-2">
						<div className="flex items-start justify-between gap-4">
							<div>
								<p className="text-muted-foreground text-xs font-medium uppercase">
									Current regime
								</p>
								<div className="mt-3 flex items-center gap-3">
									{intelligence.isLoading ? (
										<>
											<Skeleton className="h-8 w-24 rounded-md" />
											<span className="text-muted-foreground text-xs">Detecting...</span>
										</>
									) : (
										<RegimeBadge label={regimeData?.current_regime} size="lg" />
									)}
								</div>
							</div>
							<div className="bg-primary/10 text-primary flex size-10 items-center justify-center rounded-md">
								<Activity className="size-5" />
							</div>
						</div>
						<RegimeStateRail currentRegime={regimeData?.current_regime} />
						<div className="mt-6">
							<div className="mb-2 flex items-center justify-between text-xs">
								<span className="text-muted-foreground">State fit probability</span>
								<span className="num font-medium">{formatPercent(regimeConfidence)}</span>
							</div>
							<Progress
								value={
									intelligence.isLoading
										? 38
										: Math.max(0, Math.min(100, (regimeConfidence ?? 0) * 100))
								}
								indicatorClassName={
									intelligence.isLoading ? 'upload-progress-indicator' : undefined
								}
							/>
						</div>
						<p className="text-muted-foreground mt-5 text-sm leading-6">
							{intelligence.isLoading
								? 'Analyzing validated market and portfolio features for the current state.'
								: regimeNarrative(regimeData?.current_regime)}
						</p>
						<Button asChild variant="link" size="sm" className="mt-2 h-auto px-0">
							<Link href="/regime">
								Review regime evidence <ArrowRight className="size-3.5" />
							</Link>
						</Button>
					</Card>
				</Reveal>
			)}

			<Reveal className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
				<MetricCard
					label="Health score"
					value={`${health.score}/100`}
					hint={`${health.category} · ${health.trend}`}
					tooltip="A composite view of return, drawdown, volatility, diversification, regime, and data quality."
					icon={<HeartPulse className="size-4" />}
				/>
				<MetricCard
					label="Max drawdown"
					value={formatPercent(maxDrawdown)}
					hint="Largest peak-to-trough decline"
					tooltip="The worst decline from a portfolio peak during the selected analytics history."
					tone={(maxDrawdown ?? 0) < -0.2 ? 'negative' : 'neutral'}
					icon={<LineChart className="size-4" />}
					loading={intelligence.isLoading}
					explanation={{ portfolioId, metric: 'max_drawdown' }}
				/>
				<MetricCard
					label="Annualized volatility"
					value={formatPercent(annualizedVolatility)}
					hint="Observed return variability"
					tooltip="Daily return variability scaled to a 252-trading-day year. Higher values imply a wider range of outcomes."
					icon={<Activity className="size-4" />}
					loading={intelligence.isLoading}
					explanation={{ portfolioId, metric: 'annualized_volatility' }}
				/>
				<MetricCard
					label="Historical VaR"
					value={formatPercent(historicalVar)}
					hint="One-day loss threshold"
					tooltip="At the selected confidence level, historical VaR estimates the daily return threshold exceeded only in the worst tail observations."
					icon={<ShieldCheck className="size-4" />}
					loading={intelligence.isLoading}
					explanation={{ portfolioId, metric: 'historical_var' }}
				/>
			</Reveal>

			<Reveal>
				<SectionCard
					title="Continue your analysis"
					description="Move directly from the snapshot to the workflow you need."
				>
					<div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
						<WorkflowLink href="/trades" icon={ReceiptText} label="Update trades" />
						<WorkflowLink href="/risk" icon={ShieldCheck} label="Inspect risk" />
						<WorkflowLink href="/regime" icon={Activity} label="Explore regimes" />
						<WorkflowLink href="/ai-copilot" icon={Bot} label="Explain with AI" />
					</div>
				</SectionCard>
			</Reveal>

			<Reveal className="grid gap-4 xl:grid-cols-[minmax(20rem,0.85fr)_minmax(0,1.15fr)]">
				<SectionCard
					title="Sector allocation"
					description="Current portfolio value grouped by the economic exposure behind each holding."
				>
					{intelligence.isLoading ? (
						<MetricGridSkeleton count={2} />
					) : sectorAllocation.length ? (
						<SectorAllocationChart data={sectorAllocation} currency={currency} />
					) : (
						<EmptyState
							title="No sector exposure available"
							description="Add open positions to build the portfolio allocation."
						/>
					)}
				</SectionCard>
				<SectionCard
					title="Largest positions"
					description="Open holdings ranked by portfolio weight."
				>
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
			</Reveal>

			<Reveal className="grid gap-4 lg:grid-cols-2">
				<ChartCard
					title="Cumulative return path"
					description="Compounded portfolio return across the available history."
					action={<ChartValue label="Period return" value={formatPercent(periodReturn)} />}
				>
					{chartsLoading ? (
						<MetricGridSkeleton count={2} />
					) : chartCumulative.length ? (
						<SeriesLineChart data={chartCumulative} gradient />
					) : (
						<EmptyState
							title="No return series available"
							description="Add trades and refresh market data to build this history."
						/>
					)}
				</ChartCard>
				<ChartCard
					title="Drawdown path"
					description="Distance below the previous portfolio peak."
					action={<ChartValue label="Worst drawdown" value={formatPercent(worstDrawdown)} />}
				>
					{chartsLoading ? (
						<MetricGridSkeleton count={2} />
					) : chartDrawdown.length ? (
						<SeriesAreaChart data={chartDrawdown} />
					) : (
						<EmptyState
							title="No drawdown series available"
							description="Drawdown appears once a return history is available."
						/>
					)}
				</ChartCard>
			</Reveal>

			<Reveal>
				<SectionCard
					title="Priority recommendations"
					description="The strongest portfolio, sector, risk, and regime signals to review first."
				>
					{intelligence.isLoading ? (
						<MetricGridSkeleton count={2} />
					) : recommendations.length ? (
						<div className="grid gap-x-5 divide-y sm:grid-cols-2 sm:divide-y-0 xl:grid-cols-3">
							{recommendations.map((item) => (
								<div
									key={item.id}
									className="border-border py-3 sm:border-t sm:first:border-t-0 xl:border-t-0"
								>
									<div className="flex flex-wrap gap-2">
										<SeverityBadge severity={item.severity} />
										<CategoryBadge category={item.category} />
									</div>
									<p className="mt-2 text-sm font-medium">{item.title}</p>
									<p className="text-muted-foreground mt-1 text-xs leading-5">{item.action}</p>
								</div>
							))}
							<Button
								asChild
								size="sm"
								variant="outline"
								className="mt-3 sm:col-span-2 xl:col-span-3 xl:w-fit"
							>
								<Link href="/recommendations">View recommendation center</Link>
							</Button>
						</div>
					) : (
						<EmptyState
							title="No active recommendations"
							description="Recommendations appear as risk and regime evidence becomes available."
						/>
					)}
				</SectionCard>
			</Reveal>
		</div>
	);
}

function DashboardDatum({ label, value }: { label: string; value: string }) {
	return (
		<div>
			<p className="text-muted-foreground text-xs">{label}</p>
			<p className="num mt-1 font-medium">{value}</p>
		</div>
	);
}

function ChartValue({ label, value }: { label: string; value: string }) {
	return (
		<div className="text-right">
			<p className="text-muted-foreground text-[11px] font-medium uppercase">{label}</p>
			<p className="num mt-0.5 text-sm font-semibold">{value}</p>
		</div>
	);
}

function WorkflowLink({
	href,
	icon: Icon,
	label
}: {
	href: string;
	icon: typeof Activity;
	label: string;
}) {
	return (
		<Button asChild variant="outline" className="h-11 justify-between px-3">
			<Link href={href}>
				<span className="inline-flex items-center gap-2">
					<Icon className="text-muted-foreground size-4" /> {label}
				</span>
				<ArrowRight className="text-muted-foreground size-3.5" />
			</Link>
		</Button>
	);
}

function regimeNarrative(regime?: string) {
	const value = (regime ?? '').toLowerCase();
	if (value.includes('bull'))
		return 'The model sees a constructive return and volatility pattern. Keep position concentration in view.';
	if (value.includes('bear'))
		return 'Downside pressure is dominant. Review drawdown, liquidity, and oversized positions before adding risk.';
	if (value.includes('crisis'))
		return 'Market stress is elevated. Prioritize capital preservation and verify data freshness before acting.';
	if (value.includes('vol'))
		return 'Return dispersion is elevated. Position sizing and risk limits matter more than directional conviction.';
	return 'The model needs more validated history before it can describe the current market state reliably.';
}
