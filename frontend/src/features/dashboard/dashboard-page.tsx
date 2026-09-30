'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { Activity, ArrowRight, Bot, HeartPulse, ShieldCheck, Upload } from 'lucide-react';

import { ChartCard, SectionCard } from '@/components/charts/chart-card';
import { DataTable, type Column } from '@/components/common/data-table';
import { InlineSpinner, MetricCard } from '@/components/common/metric-card';
import { EmptyState, ErrorState, WarningState } from '@/components/common/states';
import { PnLValue, RegimeBadge, SeverityBadge } from '@/components/domain/finance';
import { NoTradesState, RequirePortfolio } from '@/components/layout/require-portfolio';
import { PageHeader } from '@/components/layout/top-bar';
import { Reveal } from '@/components/motion/reveal';
import { Badge } from '@/components/ui/badge';
import {
	Accordion,
	AccordionContent,
	AccordionItem,
	AccordionTrigger
} from '@/components/ui/accordion';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { metric } from '@/lib/analytics-derive';
import { useIntelligence } from '@/lib/api/intelligence';
import { useSummary } from '@/lib/api/portfolio';
import { formatCurrency, formatDate, formatNumber, formatPercent, toSeries } from '@/lib/format';
import { useSelectedPortfolio } from '@/lib/portfolio-context';
import type { Position } from '@/lib/types';
import { DashboardGuide } from './dashboard-guide';

const SectorAllocationChart = dynamic(
	() => import('@/components/charts/sector-allocation-chart').then((m) => m.SectorAllocationChart),
	{ ssr: false, loading: () => <Skeleton className="h-56 w-full" /> }
);
const SeriesLineChart = dynamic(
	() => import('@/components/charts/series-charts').then((m) => m.SeriesLineChart),
	{ ssr: false, loading: () => <Skeleton className="h-56 w-full" /> }
);
const SeriesAreaChart = dynamic(
	() => import('@/components/charts/series-charts').then((m) => m.SeriesAreaChart),
	{ ssr: false, loading: () => <Skeleton className="h-56 w-full" /> }
);

export default function DashboardPage() {
	return (
		<RequirePortfolio label="your overview">
			{(id) => <Dashboard key={id} portfolioId={id} />}
		</RequirePortfolio>
	);
}

function Dashboard({ portfolioId }: { portfolioId: string }) {
	const { selected } = useSelectedPortfolio();
	const intelligence = useIntelligence(portfolioId);
	const data = intelligence.data;
	const savedSummary = useSummary(portfolioId, !data);
	const summary = data?.summary ?? savedSummary.data;
	const risk = data?.risk ?? undefined;
	const regime = data?.regime;
	const review = risk?.review;
	const currency = summary?.base_currency ?? selected?.base_currency ?? 'INR';
	const positions = (data?.positions ?? []).filter((p) => p.quantity > 0);
	const topPositions = [...positions]
		.sort((a, b) => (b.market_weight ?? 0) - (a.market_weight ?? 0))
		.slice(0, 6);
	const priority = data?.recommendations[0];
	const cumulative = toSeries(risk?.series?.cumulative_returns);
	const drawdown = toSeries(risk?.series?.drawdown);
	const period = risk?.methodology;
	const columns: Column<Position>[] = [
		{
			key: 'ticker',
			header: 'Holding',
			cell: (row) => (
				<div className="py-1">
					<p className="font-medium">{row.ticker}</p>
					<p className="text-muted-foreground mt-0.5 text-xs">{row.sector ?? 'Unclassified'}</p>
				</div>
			)
		},
		{
			key: 'weight',
			header: 'Weight',
			align: 'right',
			cell: (row) => formatPercent(row.market_weight)
		},
		{
			key: 'value',
			header: 'Market value',
			align: 'right',
			cell: (row) => formatCurrency(row.market_value, currency)
		}
	];

	return (
		<div className="space-y-7 sm:space-y-8">
			<PageHeader
				title={selected?.name ?? 'Portfolio overview'}
				description="What you own. Where your risk sits. What to review next."
				actions={
					<>
						<DashboardGuide portfolioId={portfolioId} />
						<Button asChild size="sm" variant="outline">
							<Link href="/upload">
								<Upload className="size-4" /> Upload CSV
							</Link>
						</Button>
					</>
				}
			/>
			{intelligence.isError ? (
				<ErrorState error={intelligence.error} onRetry={() => void intelligence.refetch()} />
			) : null}
			{intelligence.isLoading ? (
				<div className="space-y-6">
					{summary ? (
						<section
							aria-label="Saved holdings"
							className="grid gap-4 border-b pb-5 sm:grid-cols-3"
						>
							<Datum
								label="Remaining cost basis"
								value={formatCurrency(summary.invested_value, currency)}
							/>
							<Datum label="Trades saved" value={String(summary.trades_count)} />
							<Datum
								label="Current holdings value"
								value={formatCurrency(summary.current_value, currency)}
							/>
						</section>
					) : null}
					<div role="status" className="flex flex-wrap items-center gap-3">
						<InlineSpinner label="Preparing your risk reading" />
						<span className="text-muted-foreground text-xs">
							Your trades are saved. The first reading also loads price history.
						</span>
					</div>
					<div className="grid gap-4 lg:grid-cols-2">
						{['Current-holdings model return', 'Modeled drawdown'].map((title) => (
							<ChartCard key={title} title={title}>
								<Skeleton className="h-56 w-full" />
							</ChartCard>
						))}
					</div>
				</div>
			) : !data ? null : (
				<>
					{summary?.trades_count === 0 ? <NoTradesState /> : null}
					{selected?.is_demo ? (
						<Badge variant="outline">Demo portfolio · illustrative data</Badge>
					) : null}
					<Reveal className="grid gap-6 border-b pb-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
						<section aria-label="Holdings value" className="min-w-0">
							<div className="flex flex-wrap items-center justify-between gap-2">
								<h2 className="text-muted-foreground text-sm font-normal">
									Current holdings value
								</h2>
								<span className="text-muted-foreground text-xs">Latest available prices</span>
							</div>
							<p
								data-testid="holdings-value"
								className="num mt-3 break-words text-3xl font-medium leading-tight sm:text-4xl"
							>
								{formatCurrency(summary?.current_value, currency)}
							</p>
							<dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-[1.1fr_1.3fr_0.8fr]">
								<div className="min-w-0">
									<dt className="text-muted-foreground text-xs">Open-holding return</dt>
									<dd data-testid="holdings-return" className="mt-1 text-xl font-medium">
										<PnLValue value={summary?.total_return} percent />
									</dd>
								</div>
								<Datum
									label="Remaining cost basis"
									value={formatCurrency(summary?.invested_value, currency)}
								/>
								<Datum label="Open holdings" value={formatNumber(positions.length, 0)} />
							</dl>
							<p className="text-muted-foreground mt-4 text-xs leading-5">
								Return on shares you still own. Completed sales are shown in the breakdown below.
							</p>
							<Accordion type="single" collapsible className="mt-4 border-t">
								<AccordionItem value="profit-loss" className="border-0">
									<AccordionTrigger className="gap-3 rounded-sm py-3 text-xs transition-colors duration-200 hover:text-primary hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
										Profit / loss breakdown
									</AccordionTrigger>
									<AccordionContent className="pb-1">
										<dl className="grid gap-4 sm:grid-cols-3">
											<Datum
												label="Unrealized profit / loss"
												value={formatCurrency(summary?.unrealized_pnl, currency)}
											/>
											<Datum
												label="Realized profit / loss"
												value={formatCurrency(summary?.realized_pnl, currency)}
											/>
											<Datum
												label="Total profit / loss"
												value={formatCurrency(summary?.total_pnl, currency)}
											/>
										</dl>
										<p className="text-muted-foreground mt-3 text-xs leading-5">
											Total profit / loss includes completed sales. Open-holding return compares
											current holdings value with their remaining purchase cost, excluding completed
											sales.
										</p>
									</AccordionContent>
								</AccordionItem>
							</Accordion>
						</section>
						<section
							aria-label="Next review"
							className="min-w-0 border-t pt-5 xl:border-l xl:border-t-0 xl:pl-6 xl:pt-0"
						>
							<div className="mb-3 flex flex-wrap items-center justify-between gap-2">
								<p className="text-muted-foreground text-xs font-medium">Start here</p>
								{priority ? <SeverityBadge severity={priority.severity} /> : null}
							</div>
							{priority ? (
								<>
									<h2 className="max-w-lg text-lg font-medium leading-snug">{priority.title}</h2>
									<p className="text-muted-foreground mt-3 border-l-2 border-primary/40 pl-3 text-xs leading-5">
										{priority.evidence}
									</p>
									<p className="mt-3 text-sm leading-6">{priority.action}</p>
									<div className="mt-4 flex flex-wrap gap-2">
										<Button asChild size="sm">
											<Link href="/recommendations">
												Review evidence <ArrowRight className="size-4" />
											</Link>
										</Button>
										<Button asChild size="sm" variant="ghost">
											<Link
												href={`/ai-copilot?prompt=${encodeURIComponent(`Explain this recommendation: ${priority.title}`)}`}
											>
												<Bot className="size-4" /> Explain this
											</Link>
										</Button>
									</div>
								</>
							) : (
								<>
									<h2 className="text-lg font-medium">Build your first risk reading</h2>
									<p className="text-muted-foreground mt-2 text-sm">
										Recommendations need holdings and price history. Missing evidence does not mean
										there is no risk.
									</p>
									<Button asChild variant="outline" size="sm" className="mt-4">
										<Link href="/risk">
											Review available data <ArrowRight className="size-4" />
										</Link>
									</Button>
								</>
							)}
						</section>
					</Reveal>
					{data.warnings.length ? (
						<WarningState
							title="Some evidence is incomplete"
							description={data.warnings.join(' ')}
						/>
					) : null}
					<section aria-label="Portfolio history" className="space-y-3">
						<div className="flex flex-wrap items-baseline justify-between gap-2">
							<h2 className="text-base font-medium">Historical perspective</h2>
							<p className="text-muted-foreground text-xs">
								{period
									? `${formatDate(period.start_date)} to ${formatDate(period.end_date)} · ${period.observations} observations`
									: 'Waiting for price history'}
							</p>
						</div>
						<p className="text-muted-foreground text-xs">
							A model of today's holdings, not your actual trade-by-trade performance.
						</p>
						<div className="grid gap-4 lg:grid-cols-2">
							<ChartCard
								title="Current-holdings model return"
								description="Fixed cost weights, rebalanced daily."
								className="pb-3 pt-0"
								action={
									<div className="text-right">
										<p className="text-muted-foreground text-xs">Modeled period return</p>
										<p data-testid="modeled-return" className="num mt-1 text-lg font-medium">
											{formatPercent(cumulative.at(-1)?.value)}
										</p>
									</div>
								}
							>
								{cumulative.length ? (
									<SeriesLineChart data={cumulative} gradient />
								) : (
									<EmptyState title="No modeled history" />
								)}
							</ChartCard>
							<ChartCard
								title="Modeled drawdown"
								description="Distance below the model's previous peak."
								className="pb-3 pt-0"
								action={
									<div className="text-right">
										<p className="text-muted-foreground text-xs">Largest historical fall</p>
										<p className="num mt-1 text-lg font-medium">
											{formatPercent(metric(risk, 'max_drawdown'))}
										</p>
									</div>
								}
							>
								{drawdown.length ? (
									<SeriesAreaChart data={drawdown} height={240} />
								) : (
									<EmptyState title="No modeled history" />
								)}
							</ChartCard>
						</div>
					</section>
					<section aria-label="Risk snapshot" className="space-y-3">
						<div className="flex flex-wrap items-center justify-between gap-2">
							<h2 className="text-base font-medium">Risk of your current holdings</h2>
							<Button asChild variant="link" size="sm" className="h-auto px-0 text-xs">
								<Link href="/portfolio-health">
									Understand this review <ArrowRight className="size-3.5" />
								</Link>
							</Button>
						</div>
						<p className="text-muted-foreground text-xs leading-5">
							Based on the modeled history above. Historical estimates, not a forecast or safety
							rating.
						</p>
						<Reveal className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
							<MetricCard
								label="Risk-review score"
								value={review?.score == null ? 'Unavailable' : `${review.score}/100`}
								hint={review?.category ?? 'Waiting for risk data'}
								tooltip="An uncalibrated historical review aid, not a safety rating. See Risk Review for the formula and missing inputs."
								icon={<HeartPulse className="size-4" />}
							/>
							<MetricCard
								label="Largest historical fall"
								value={formatPercent(metric(risk, 'max_drawdown'))}
								hint="Modeled peak-to-trough decline"
								icon={<Activity className="size-4" />}
								explanation={{ portfolioId, metric: 'max_drawdown' }}
							/>
							<MetricCard
								label="Return variability"
								value={formatPercent(metric(risk, 'annualized_volatility'))}
								hint="Annualized volatility"
								icon={<Activity className="size-4" />}
								explanation={{ portfolioId, metric: 'annualized_volatility' }}
							/>
							<MetricCard
								label="One-day downside threshold"
								value={formatPercent(metric(risk, 'historical_var'))}
								hint="Historical VaR · 95% level"
								icon={<ShieldCheck className="size-4" />}
								explanation={{ portfolioId, metric: 'historical_var' }}
							/>
						</Reveal>
					</section>
					<Reveal className="grid gap-6 border-t pt-6 xl:grid-cols-2 xl:gap-8">
						<SectionCard
							title="Sector allocation"
							description="Where your current holdings value is concentrated."
							className="border-0 py-0"
						>
							{data.sector_allocation.length ? (
								<SectorAllocationChart data={data.sector_allocation} currency={currency} />
							) : (
								<EmptyState
									title="Sector values unavailable"
									description="Open holdings and market prices are needed to calculate exposure."
								/>
							)}
						</SectionCard>
						<SectionCard
							title="Largest positions"
							description="Up to six holdings, ranked by portfolio weight."
							className="border-0 py-0"
						>
							<DataTable
								dense
								columns={columns}
								rows={topPositions}
								rowKey={(r) => r.ticker}
								empty={<EmptyState title="No open holdings" />}
							/>
							<Button asChild variant="link" size="sm" className="mt-3 px-0">
								<Link href={`/portfolios/${portfolioId}`}>
									View all holdings <ArrowRight className="size-3.5" />
								</Link>
							</Button>
						</SectionCard>
					</Reveal>
					<section
						className="flex flex-col gap-4 border-y py-5 sm:flex-row sm:items-center sm:justify-between"
						aria-label="Market context"
					>
						<div className="min-w-0 space-y-2">
							<div className="flex flex-wrap items-center gap-3">
								<h2 className="text-base font-medium">Market context</h2>
								<RegimeBadge label={regime?.current_regime} />
								<Badge variant="outline">
									{regime?.fallback_used
										? 'Rule-based estimate'
										: regime
											? 'Model estimate'
											: 'Unavailable'}
								</Badge>
							</div>
							<p className="text-muted-foreground max-w-2xl text-sm">
								{regime?.explanation?.summary ?? 'More market history is needed.'} This describes
								observed conditions, not the next market move.
							</p>
						</div>
						<Button asChild variant="outline" size="sm">
							<Link href="/regime">
								View evidence <ArrowRight className="size-3.5" />
							</Link>
						</Button>
					</section>
				</>
			)}
		</div>
	);
}

function Datum({ label, value }: { label: string; value: string }) {
	return (
		<div className="min-w-0">
			<dt className="text-muted-foreground text-xs">{label}</dt>
			<dd className="num mt-1 break-words text-base font-medium">{value}</dd>
		</div>
	);
}
