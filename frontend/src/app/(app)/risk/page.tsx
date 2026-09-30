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
import {
	Accordion,
	AccordionContent,
	AccordionItem,
	AccordionTrigger
} from '@/components/ui/accordion';
import { metric } from '@/lib/analytics-derive';
import { formatDate, formatPercent, formatRisk, toSeries } from '@/lib/format';
import { useRisk } from '@/lib/queries';
import type { RiskParams } from '@/lib/api/analytics';

const METRICS = [
	{
		label: 'Modeled period return',
		names: ['period_return', 'total_return'],
		kind: 'pct',
		explanation: 'period_return'
	},
	{ label: 'CAGR', names: ['cagr'], kind: 'pct', explanation: 'cagr' },
	{
		label: 'Volatility',
		names: ['annualized_volatility', 'volatility'],
		kind: 'pct',
		explanation: 'annualized_volatility'
	},
	{ label: 'Max drawdown', names: ['max_drawdown'], kind: 'pct', explanation: 'max_drawdown' },
	{
		label: 'Historical VaR',
		names: ['historical_var'],
		kind: 'pct',
		explanation: 'historical_var'
	},
	{
		label: 'Historical CVaR',
		names: ['historical_cvar'],
		kind: 'pct',
		explanation: 'historical_cvar'
	},
	{ label: 'Sharpe', names: ['sharpe'], kind: 'num', explanation: 'sharpe' },
	{ label: 'Sortino', names: ['sortino'], kind: 'num', explanation: 'sortino' },
	{ label: 'Calmar', names: ['calmar'], kind: 'num', explanation: 'calmar' },
	{
		label: 'Parametric VaR',
		names: ['parametric_var'],
		kind: 'pct',
		explanation: 'parametric_var'
	},
	{
		label: 'Parametric CVaR',
		names: ['parametric_cvar'],
		kind: 'pct',
		explanation: 'parametric_cvar'
	},
	{
		label: 'Daily mean',
		names: ['daily_mean_return'],
		kind: 'pct',
		explanation: 'daily_mean_return'
	}
] as const;

export default function RiskRoutePage() {
	return (
		<RequirePortfolio label="risk analytics">
			{(id) => <RiskPage key={id} portfolioId={id} />}
		</RequirePortfolio>
	);
}

function RiskPage({ portfolioId }: { portfolioId: string }) {
	const [startDate, setStartDate] = useState('');
	const [endDate, setEndDate] = useState('');
	const [confidence, setConfidence] = useState(0.95);
	const [riskFree, setRiskFree] = useState(0.06);
	const [window, setWindow] = useState(20);

	const [params, setParams] = useState<RiskParams>({});
	const risk = useRisk(portfolioId, params);
	const chartDaily = toSeries(risk.data?.series?.daily_returns);
	const chartCumulative = toSeries(risk.data?.series?.cumulative_returns);
	const chartDrawdown = toSeries(risk.data?.series?.drawdown);
	const rollingVol = toSeries(risk.data?.series?.rolling_volatility);
	const rollingRet = toSeries(risk.data?.series?.rolling_returns);

	return (
		<div className="space-y-4">
			<PageHeader
				title="Risk Analytics"
				description="A historical stress reading of today's holdings. Not a reconstruction of your investment returns."
				actions={
					<Button size="sm" variant="outline" onClick={() => void risk.refetch()}>
						<RefreshCw className="size-3.5" /> Recalculate
					</Button>
				}
			/>

			<p className="text-muted-foreground text-sm">
				{risk.data?.methodology
					? `${formatDate(risk.data.methodology.start_date)} to ${formatDate(risk.data.methodology.end_date)} · ${risk.data.methodology.observations} daily observations`
					: 'Default: all available history, matching the dashboard.'}
			</p>
			<Accordion type="single" collapsible>
				<AccordionItem value="parameters">
					<AccordionTrigger>Adjust analysis period and assumptions</AccordionTrigger>
					<AccordionContent>
						<form
							onSubmit={(event) => {
								event.preventDefault();
								setParams({
									start_date: startDate || undefined,
									end_date: endDate || undefined,
									confidence_level: confidence,
									risk_free_rate: riskFree,
									rolling_window: window
								});
							}}
						>
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
										required
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
										min="0"
										max="1"
										required
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
										max="252"
										required
										value={window}
										onChange={(event) => setWindow(Number(event.target.value))}
										className="h-9 w-[7rem]"
									/>
								</div>
							</div>
							<Button type="submit" size="sm" className="mt-4" disabled={risk.isFetching}>
								Apply assumptions
							</Button>
							<p className="text-muted-foreground mt-2 text-xs">
								Leave dates blank for all available history. Custom calculations do not replace the
								dashboard snapshot.
							</p>
						</form>
					</AccordionContent>
				</AccordionItem>
			</Accordion>

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
								explanation={
									Object.keys(params).length === 0
										? { portfolioId, metric: item.explanation }
										: undefined
								}
							/>
						);
					})}
				</div>
			)}

			<div className="grid gap-4 lg:grid-cols-2">
				<ChartCard
					title="Current-holdings model return"
					description="Fixed cost weights applied to historical prices; not actual performance."
				>
					{chartCumulative.length ? (
						<SeriesLineChart data={chartCumulative} gradient />
					) : (
						<EmptyState title="No series" />
					)}
				</ChartCard>
				<ChartCard title="Drawdown">
					{chartDrawdown.length ? (
						<SeriesAreaChart data={chartDrawdown} />
					) : (
						<EmptyState title="No series" />
					)}
				</ChartCard>
				<ChartCard title={`Rolling volatility (${params.rolling_window ?? 20}d)`}>
					{rollingVol.length ? (
						<SeriesLineChart data={rollingVol} color="var(--chart-3)" />
					) : (
						<EmptyState title="No series" />
					)}
				</ChartCard>
				<ChartCard title={`Rolling returns (${params.rolling_window ?? 20}d)`}>
					{rollingRet.length ? (
						<SeriesLineChart data={rollingRet} color="var(--chart-4)" />
					) : (
						<EmptyState title="No series" />
					)}
				</ChartCard>
				<ChartCard title="Daily returns" className="lg:col-span-2">
					{chartDaily.length ? (
						<SeriesBarChart data={chartDaily} />
					) : (
						<EmptyState title="No series" />
					)}
				</ChartCard>
			</div>
		</div>
	);
}
