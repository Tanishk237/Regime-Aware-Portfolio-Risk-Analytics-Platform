'use client';

import { Download, Play, RefreshCw } from 'lucide-react';
import { useMemo, useState } from 'react';
import { toast } from 'sonner';

import { SectionCard } from '@/components/charts/chart-card';
import { DataTable, type Column } from '@/components/common/data-table';
import { MetricCard } from '@/components/common/metric-card';
import { EmptyState, ErrorState, LoadingSkeleton } from '@/components/common/states';
import { RequirePortfolio } from '@/components/layout/require-portfolio';
import { PageHeader } from '@/components/layout/top-bar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Textarea } from '@/components/ui/textarea';
import { metric } from '@/lib/analytics-derive';
import { formatCurrency, formatNumber, formatPercent } from '@/lib/format';
import { usePositions, useRisk, useSummary } from '@/lib/queries';
import type { Position } from '@/lib/types';

type ScenarioResult = {
	name: string;
	description: string;
	marketShock: number;
	volatilityShock: number;
	valueBefore: number;
	valueAfter: number;
	estimatedLoss: number;
	estimatedLossPct: number;
	estimatedVarAfter?: number;
	generatedAt: string;
};

export default function StressTestsRoutePage() {
	return (
		<RequirePortfolio label="stress testing">
			{(id) => <StressTestsPage portfolioId={id} />}
		</RequirePortfolio>
	);
}

function StressTestsPage({ portfolioId }: { portfolioId: string }) {
	const summary = useSummary(portfolioId);
	const positions = usePositions(portfolioId);
	const risk = useRisk(portfolioId);
	const [name, setName] = useState('Market drawdown scenario');
	const [description, setDescription] = useState('Broad market decline with higher volatility.');
	const [marketShock, setMarketShock] = useState(-20);
	const [volatilityShock, setVolatilityShock] = useState(25);
	const [result, setResult] = useState<ScenarioResult | null>(null);

	const currency = summary.data?.base_currency ?? 'INR';
	const valueBefore = summary.data?.current_value ?? summary.data?.invested_value ?? 0;
	const positionRows = useMemo(
		() =>
			(positions.data ?? []).map((position) => {
				const before = position.market_value ?? position.cost_basis ?? 0;
				const after = before * (1 + marketShock / 100);
				return { ...position, scenario_value: after, scenario_pnl: after - before };
			}),
		[marketShock, positions.data]
	);

	const runScenario = () => {
		if (!valueBefore) {
			toast.error('Portfolio value is unavailable for stress testing.');
			return;
		}
		const valueAfter = valueBefore * (1 + marketShock / 100);
		const historicalVar = metric(risk.data, 'historical_var');
		const estimatedVarAfter =
			historicalVar === undefined || historicalVar === null
				? undefined
				: historicalVar * (1 + volatilityShock / 100);
		const next = {
			name: name.trim() || 'Untitled stress scenario',
			description: description.trim(),
			marketShock,
			volatilityShock,
			valueBefore,
			valueAfter,
			estimatedLoss: valueAfter - valueBefore,
			estimatedLossPct: valueBefore ? (valueAfter - valueBefore) / valueBefore : 0,
			estimatedVarAfter,
			generatedAt: new Date().toISOString()
		};
		setResult(next);
		toast.success('Stress scenario generated');
	};

	const columns: Array<Column<Position & { scenario_value: number; scenario_pnl: number }>> = [
		{
			key: 'ticker',
			header: 'Ticker',
			cell: (row) => <span className="font-medium">{row.ticker}</span>
		},
		{
			key: 'weight',
			header: 'Weight',
			align: 'right',
			cell: (row) => formatPercent(row.weight ?? row.market_weight ?? row.cost_weight)
		},
		{
			key: 'before',
			header: 'Before',
			align: 'right',
			cell: (row) => formatCurrency(row.market_value ?? row.cost_basis, currency)
		},
		{
			key: 'after',
			header: 'After',
			align: 'right',
			cell: (row) => formatCurrency(row.scenario_value, currency)
		},
		{
			key: 'pnl',
			header: 'Scenario P&L',
			align: 'right',
			cell: (row) => (
				<span className={row.scenario_pnl < 0 ? 'text-negative' : 'text-positive'}>
					{formatCurrency(row.scenario_pnl, currency)}
				</span>
			)
		}
	];

	return (
		<div className="space-y-4">
			<PageHeader
				title="Stress Tests"
				description="Estimate portfolio impact under market shock and volatility stress assumptions."
				actions={
					<Button
						size="sm"
						variant="outline"
						onClick={() => {
							void summary.refetch();
							void positions.refetch();
							void risk.refetch();
						}}
					>
						<RefreshCw className="size-3.5" /> Refresh
					</Button>
				}
			/>

			<SectionCard title="Scenario">
				<div className="grid gap-4 lg:grid-cols-2">
					<div className="grid gap-1.5">
						<Label htmlFor="scenario-name">Name</Label>
						<Input
							id="scenario-name"
							value={name}
							onChange={(event) => setName(event.target.value)}
						/>
					</div>
					<div className="grid gap-1.5 lg:row-span-2">
						<Label htmlFor="scenario-description">Description</Label>
						<Textarea
							id="scenario-description"
							value={description}
							onChange={(event) => setDescription(event.target.value)}
						/>
					</div>
					<div className="grid gap-4 sm:grid-cols-2">
						<div className="grid gap-2">
							<Label>Market shock: {marketShock}%</Label>
							<Slider
								value={[marketShock]}
								min={-60}
								max={30}
								step={1}
								onValueChange={([value]) => setMarketShock(value ?? -20)}
							/>
						</div>
						<div className="grid gap-2">
							<Label>Volatility shock: +{volatilityShock}%</Label>
							<Slider
								value={[volatilityShock]}
								min={0}
								max={150}
								step={5}
								onValueChange={([value]) => setVolatilityShock(value ?? 25)}
							/>
						</div>
					</div>
				</div>
				<div className="mt-4 flex flex-wrap gap-2">
					<Button onClick={runScenario}>
						<Play className="size-4" /> Run scenario
					</Button>
					<Button variant="outline" disabled={!result} onClick={() => result && download(result)}>
						<Download className="size-4" /> Export JSON
					</Button>
				</div>
			</SectionCard>

			<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
				<MetricCard
					label="Value before"
					value={formatCurrency(valueBefore, currency)}
					loading={summary.isLoading}
				/>
				<MetricCard
					label="Value after"
					value={formatCurrency(result?.valueAfter, currency)}
					tone={result && result.valueAfter >= result.valueBefore ? 'positive' : 'negative'}
				/>
				<MetricCard
					label="Estimated impact"
					value={formatCurrency(result?.estimatedLoss, currency)}
					hint={result ? formatPercent(result.estimatedLossPct) : undefined}
					tone={result && result.estimatedLoss >= 0 ? 'positive' : 'negative'}
				/>
				<MetricCard
					label="Stressed historical VaR"
					value={formatPercent(result?.estimatedVarAfter)}
					hint={`Base ${formatPercent(metric(risk.data, 'historical_var'))}`}
					loading={risk.isLoading}
				/>
			</div>

			<SectionCard title="Position impact">
				{positions.isLoading ? (
					<LoadingSkeleton rows={5} />
				) : positions.isError ? (
					<ErrorState error={positions.error} onRetry={() => void positions.refetch()} />
				) : positionRows.length === 0 ? (
					<EmptyState title="No positions available for stress testing." />
				) : (
					<DataTable
						dense
						columns={columns}
						rows={positionRows}
						rowKey={(row) => row.id ?? row.ticker}
					/>
				)}
			</SectionCard>

			<SectionCard title="Method">
				<p className="text-muted-foreground text-sm">
					This frontend scenario applies the selected market shock uniformly to current position
					values and scales historical VaR by the volatility shock. Backend persisted stress testing
					can replace this local estimator when scenario APIs are added.
				</p>
				<p className="text-muted-foreground mt-2 text-xs">
					Positions loaded: {formatNumber(positionRows.length, 0)}
				</p>
			</SectionCard>
		</div>
	);
}

function download(result: ScenarioResult) {
	const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
	const url = URL.createObjectURL(blob);
	const link = document.createElement('a');
	link.href = url;
	link.download = `${result.name.toLowerCase().replace(/\s+/g, '-')}.json`;
	link.click();
	URL.revokeObjectURL(url);
}
