'use client';

import { RefreshCw } from 'lucide-react';
import { useState } from 'react';

import { ChartCard, SectionCard } from '@/components/charts/chart-card';
import { DataTable, type Column } from '@/components/common/data-table';
import { DateRangeControls } from '@/components/common/date-range-controls';
import { RegimeBadge } from '@/components/domain/finance';
import { MetricCard } from '@/components/common/metric-card';
import { RequirePortfolio } from '@/components/layout/require-portfolio';
import { SeriesLineChart } from '@/components/charts/series-charts';
import {
	EmptyState,
	ErrorState,
	MetricGridSkeleton,
	WarningState
} from '@/components/common/states';
import { PageHeader } from '@/components/layout/top-bar';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { daysAgo, formatDate, formatNumber, formatPercent, isoDate } from '@/lib/format';
import { useRegime } from '@/lib/queries';
import type { RegimeAnalytics } from '@/lib/types';

type StatRow = NonNullable<RegimeAnalytics['statistics']>[number];
type DurationRow = NonNullable<RegimeAnalytics['durations']>[number];
type HistoryRow = NonNullable<RegimeAnalytics['history']>[number];

export default function RegimeRoutePage() {
	return (
		<RequirePortfolio label="regime analytics">
			{(id) => <RegimePage portfolioId={id} />}
		</RequirePortfolio>
	);
}

function RegimePage({ portfolioId }: { portfolioId: string }) {
	const [startDate, setStartDate] = useState(daysAgo(365));
	const [endDate, setEndDate] = useState(isoDate(new Date()));
	const regime = useRegime(portfolioId, { start_date: startDate, end_date: endDate });
	const data = regime.data;

	const labelFor = (state: number, fallback?: string) =>
		fallback ?? data?.state_labels?.[String(state)] ?? `State ${state}`;

	const history = data?.history ?? [];
	const historySeries = history
		.filter((row) => row.date)
		.map((row) => ({ date: String(row.date), value: Number(row.hidden_state) }));

	const matrix = data?.transition_matrix ?? [];
	const confidence = data?.confidence ?? data?.probability;
	const metadata = data?.feature_metadata ?? {};
	const metadataWarnings = Array.isArray(metadata['warnings']) ? metadata['warnings'] : [];
	const modelName = typeof metadata['model_name'] === 'string' ? metadata['model_name'] : undefined;
	const isPartialResult = Boolean(data?.fallback_used || metadataWarnings.length);

	const statColumns: Array<Column<StatRow>> = [
		{
			key: 'state',
			header: 'Regime',
			cell: (row) => <RegimeBadge label={labelFor(row.hidden_state, row.label)} />
		},
		{
			key: 'count',
			header: 'Days',
			align: 'right',
			cell: (row) => <span className="num">{formatNumber(row.sample_count, 0)}</span>
		},
		{
			key: 'ret',
			header: 'Avg return',
			align: 'right',
			cell: (row) => <span className="num">{formatPercent(row.avg_return)}</span>
		},
		{
			key: 'vol',
			header: 'Avg volatility',
			align: 'right',
			cell: (row) => <span className="num">{formatPercent(row.avg_volatility)}</span>
		},
		{
			key: 'dd',
			header: 'Avg drawdown',
			align: 'right',
			cell: (row) => <span className="num">{formatPercent(row.avg_drawdown)}</span>
		},
		{
			key: 'vix',
			header: 'Avg VIX',
			align: 'right',
			cell: (row) => <span className="num">{formatNumber(row.avg_vix)}</span>
		}
	];

	const durationColumns: Array<Column<DurationRow>> = [
		{
			key: 'state',
			header: 'Regime',
			cell: (row) => <RegimeBadge label={labelFor(row.hidden_state, row.label)} />
		},
		{
			key: 'start',
			header: 'Start',
			cell: (row) => <span className="num">{formatDate(row.start_date)}</span>
		},
		{
			key: 'end',
			header: 'End',
			cell: (row) => <span className="num">{formatDate(row.end_date)}</span>
		},
		{
			key: 'days',
			header: 'Duration',
			align: 'right',
			cell: (row) => <span className="num">{formatNumber(row.duration_days, 0)} d</span>
		}
	];

	const historyColumns: Array<Column<HistoryRow>> = [
		{
			key: 'date',
			header: 'Date',
			cell: (row) => <span className="num">{formatDate(row.date)}</span>
		},
		{
			key: 'state',
			header: 'Regime',
			cell: (row) => <RegimeBadge label={labelFor(row.hidden_state, row.label)} />
		},
		{
			key: 'prob',
			header: 'Probability',
			align: 'right',
			cell: (row) => <span className="num">{formatPercent(row.probability)}</span>
		}
	];

	return (
		<div className="space-y-4">
			<PageHeader
				title="Regime Analytics"
				description="Market regimes inferred from portfolio and market features."
				actions={
					<Button size="sm" variant="outline" onClick={() => void regime.refetch()}>
						<RefreshCw className="size-3.5" /> Re-run detection
					</Button>
				}
			/>

			<SectionCard title="Detection window">
				<DateRangeControls
					startDate={startDate}
					endDate={endDate}
					onStartDate={setStartDate}
					onEndDate={setEndDate}
				/>
			</SectionCard>

			{regime.isError ? (
				<ErrorState error={regime.error} onRetry={() => void regime.refetch()} />
			) : null}
			{!regime.isError && isPartialResult ? (
				<WarningState
					title="Regime result is using available data"
					description={[
						modelName === 'deterministic_fallback'
							? 'The trained HMM was unavailable, so deterministic regime labelling was used.'
							: null,
						...metadataWarnings.map((warning) => String(warning))
					]
						.filter(Boolean)
						.join(' ')}
				/>
			) : null}

			{regime.isLoading ? (
				<MetricGridSkeleton count={5} />
			) : (
				<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
					<MetricCard
						label="Current regime"
						value={<RegimeBadge label={data?.current_regime} size="lg" />}
						hint={modelName === 'deterministic_fallback' ? 'fallback labeller' : 'HMM model'}
					/>
					<MetricCard label="Confidence" value={formatPercent(confidence)} />
					<MetricCard label="Hidden state" value={data?.current_state ?? '-'} />
					<MetricCard label="History rows" value={history.length} />
					<MetricCard label="States" value={Object.keys(data?.state_labels ?? {}).length || '-'} />
				</div>
			)}

			<div className="grid gap-4 lg:grid-cols-2">
				<ChartCard title="Regime timeline">
					{historySeries.length ? (
						<SeriesLineChart data={historySeries} percent={false} color="var(--chart-4)" />
					) : (
						<EmptyState title="No regime history available" />
					)}
				</ChartCard>

				<SectionCard title="Transition matrix">
					{matrix.length === 0 ? (
						<EmptyState title="Transition matrix unavailable" />
					) : (
						<div className="overflow-x-auto">
							<table className="w-full text-xs">
								<thead>
									<tr>
										<th className="text-muted-foreground px-2 py-1 text-left font-semibold uppercase">
											From / To
										</th>
										{matrix[0]?.map((_, index) => (
											<th key={index} className="text-muted-foreground px-2 py-1 font-semibold">
												{labelFor(index)}
											</th>
										))}
									</tr>
								</thead>
								<tbody>
									{matrix.map((row, rowIndex) => (
										<tr key={rowIndex}>
											<td className="whitespace-nowrap px-2 py-1 font-medium">
												{labelFor(rowIndex)}
											</td>
											{row.map((value, columnIndex) => (
												<td key={columnIndex} className="px-1 py-1">
													<div
														className="num rounded-md px-2 py-1.5 text-center font-medium"
														style={{
															background: `color-mix(in oklch, var(--primary) ${Math.round(
																Math.max(0, Math.min(1, value)) * 70
															)}%, transparent)`
														}}
													>
														{(value * 100).toFixed(1)}%
													</div>
												</td>
											))}
										</tr>
									))}
								</tbody>
							</table>
						</div>
					)}
				</SectionCard>
			</div>

			<Tabs defaultValue="stats">
				<TabsList>
					<TabsTrigger value="stats">Statistics</TabsTrigger>
					<TabsTrigger value="durations">Durations</TabsTrigger>
					<TabsTrigger value="history">History</TabsTrigger>
				</TabsList>
				<TabsContent value="stats" className="mt-3">
					<DataTable
						columns={statColumns}
						rows={data?.statistics ?? []}
						rowKey={(row) => String(row.hidden_state)}
						empty={<EmptyState title="No regime statistics" />}
					/>
				</TabsContent>
				<TabsContent value="durations" className="mt-3">
					<DataTable
						columns={durationColumns}
						rows={[...(data?.durations ?? [])].reverse()}
						rowKey={(row, index) => `${row.start_date}-${index}`}
						empty={<EmptyState title="No regime episodes" />}
						dense
					/>
				</TabsContent>
				<TabsContent value="history" className="mt-3">
					<DataTable
						columns={historyColumns}
						rows={[...history].reverse().slice(0, 120)}
						rowKey={(row, index) => `${row.date}-${index}`}
						empty={<EmptyState title="No regime history" />}
						dense
					/>
				</TabsContent>
			</Tabs>
		</div>
	);
}
