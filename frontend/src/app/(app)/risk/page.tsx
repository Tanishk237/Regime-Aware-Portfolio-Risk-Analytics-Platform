'use client';

import { RefreshCw } from 'lucide-react';
import { useState } from 'react';

import { ChartCard, SectionCard } from '@/components/charts/chart-card';
import { DateRangeControls } from '@/components/common/date-range-controls';
import { MetricCard } from '@/components/common/metric-card';
import { RequirePortfolio } from '@/components/layout/require-portfolio';
import {
	SeriesAreaChart,
	SeriesBarChart,
	SeriesLineChart
} from '@/components/charts/series-charts';
import { EmptyState, ErrorState, MetricGridSkeleton } from '@/components/common/states';
import { PageHeader } from '@/components/layout/top-bar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { metric } from '@/lib/analytics-derive';
import { daysAgo, formatPercent, formatRisk, isoDate, toSeries } from '@/lib/format';
import { useRisk } from '@/lib/queries';

const METRICS = [
	{ label: 'Total return', names: ['total_return'], kind: 'pct' },
	{ label: 'CAGR', names: ['cagr'], kind: 'pct' },
	{ label: 'Volatility', names: ['annualized_volatility', 'volatility'], kind: 'pct' },
	{ label: 'Max drawdown', names: ['max_drawdown'], kind: 'pct' },
	{ label: 'Historical VaR', names: ['historical_var'], kind: 'pct' },
	{ label: 'Historical CVaR', names: ['historical_cvar'], kind: 'pct' },
	{ label: 'Sharpe', names: ['sharpe'], kind: 'num' },
	{ label: 'Sortino', names: ['sortino'], kind: 'num' },
	{ label: 'Calmar', names: ['calmar'], kind: 'num' },
	{ label: 'Parametric VaR', names: ['parametric_var'], kind: 'pct' },
	{ label: 'Parametric CVaR', names: ['parametric_cvar'], kind: 'pct' },
	{ label: 'Daily mean', names: ['daily_mean_return'], kind: 'pct' }
] as const;

export default function RiskRoutePage() {
	return (
		<RequirePortfolio label="risk analytics">
			{(id) => <RiskPage portfolioId={id} />}
		</RequirePortfolio>
	);
}

function RiskPage({ portfolioId }: { portfolioId: string }) {
	const [startDate, setStartDate] = useState(daysAgo(365));
	const [endDate, setEndDate] = useState(isoDate(new Date()));
	const [confidence, setConfidence] = useState(0.95);
	const [riskFree, setRiskFree] = useState(0.06);
	const [window, setWindow] = useState(20);

	const risk = useRisk(portfolioId, {
		start_date: startDate,
		end_date: endDate,
		confidence_level: confidence,
		risk_free_rate: riskFree,
		rolling_window: window
	});

	const daily = toSeries(risk.data?.series?.daily_returns);
	const cumulative = toSeries(risk.data?.series?.cumulative_returns);
	const drawdown = toSeries(risk.data?.series?.drawdown);
	const rollingVol = toSeries(risk.data?.series?.rolling_volatility);
	const rollingRet = toSeries(risk.data?.series?.rolling_returns);

	return (
		<div className="space-y-4">
			<PageHeader
				title="Risk Analytics"
				description="CAGR, drawdown, volatility, VaR, CVaR, Sharpe, Sortino, and rolling risk."
				actions={
					<Button size="sm" variant="outline" onClick={() => void risk.refetch()}>
						<RefreshCw className="size-3.5" /> Recalculate
					</Button>
				}
			/>

			<SectionCard title="Parameters">
				<div className="flex flex-wrap items-end gap-3">
					<DateRangeControls
						startDate={startDate}
						endDate={endDate}
						onStartDate={setStartDate}
						onEndDate={setEndDate}
					/>
					<div className="grid gap-1.5">
						<Label htmlFor="conf" className="text-muted-foreground text-xs">
							Confidence
						</Label>
						<Input
							id="conf"
							type="number"
							step="0.01"
							min="0.5"
							max="0.999"
							value={confidence}
							onChange={(event) => setConfidence(Number(event.target.value))}
							className="h-9 w-[7rem]"
						/>
					</div>
					<div className="grid gap-1.5">
						<Label htmlFor="rf" className="text-muted-foreground text-xs">
							Risk-free
						</Label>
						<Input
							id="rf"
							type="number"
							step="0.005"
							value={riskFree}
							onChange={(event) => setRiskFree(Number(event.target.value))}
							className="h-9 w-[7rem]"
						/>
					</div>
					<div className="grid gap-1.5">
						<Label htmlFor="win" className="text-muted-foreground text-xs">
							Window
						</Label>
						<Input
							id="win"
							type="number"
							step="1"
							min="2"
							value={window}
							onChange={(event) => setWindow(Number(event.target.value))}
							className="h-9 w-[7rem]"
						/>
					</div>
				</div>
			</SectionCard>

			{risk.isError ? <ErrorState error={risk.error} onRetry={() => void risk.refetch()} /> : null}

			{risk.isLoading ? (
				<MetricGridSkeleton count={8} />
			) : (
				<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
					{METRICS.map((item) => {
						const value = metric(risk.data, ...item.names);
						return (
							<MetricCard
								key={item.label}
								label={item.label}
								value={
									value === undefined
										? '-'
										: item.kind === 'pct'
											? formatPercent(value)
											: formatRisk(value)
								}
							/>
						);
					})}
				</div>
			)}

			<div className="grid gap-4 lg:grid-cols-2">
				<ChartCard title="Cumulative returns">
					{cumulative.length ? (
						<SeriesLineChart data={cumulative} />
					) : (
						<EmptyState title="No series" />
					)}
				</ChartCard>
				<ChartCard title="Drawdown">
					{drawdown.length ? <SeriesAreaChart data={drawdown} /> : <EmptyState title="No series" />}
				</ChartCard>
				<ChartCard title={`Rolling volatility (${window}d)`}>
					{rollingVol.length ? (
						<SeriesLineChart data={rollingVol} color="var(--chart-3)" />
					) : (
						<EmptyState title="No series" />
					)}
				</ChartCard>
				<ChartCard title={`Rolling returns (${window}d)`}>
					{rollingRet.length ? (
						<SeriesLineChart data={rollingRet} color="var(--chart-4)" />
					) : (
						<EmptyState title="No series" />
					)}
				</ChartCard>
				<ChartCard title="Daily returns" className="lg:col-span-2">
					{daily.length ? <SeriesBarChart data={daily} /> : <EmptyState title="No series" />}
				</ChartCard>
			</div>
		</div>
	);
}
