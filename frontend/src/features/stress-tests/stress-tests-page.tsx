'use client';

import { Download, LoaderCircle, Play, RefreshCw, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

import { SectionCard } from '@/components/charts/chart-card';
import { DataTable, type Column } from '@/components/common/data-table';
import { MetricCard } from '@/components/common/metric-card';
import { EmptyState, ErrorState } from '@/components/common/states';
import { RequirePortfolio } from '@/components/layout/require-portfolio';
import { PageHeader } from '@/components/layout/top-bar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Textarea } from '@/components/ui/textarea';
import { errorMessage } from '@/lib/api';
import { formatCurrency, formatPercent } from '@/lib/format';
import { useStressScenario, useSummary } from '@/lib/queries';
import type { StressScenarioPreview, StressScenarioResult } from '@/lib/types';

type PositionImpact = StressScenarioResult['position_impacts'][number];

export default function StressTestsRoutePage() {
	return (
		<RequirePortfolio label="stress testing">
			{(id) => <StressTestsPage portfolioId={id} />}
		</RequirePortfolio>
	);
}

function StressTestsPage({ portfolioId }: { portfolioId: string }) {
	const summary = useSummary(portfolioId);
	const stress = useStressScenario(portfolioId);
	const [prompt, setPrompt] = useState('What if NIFTY falls 15% and volatility rises 40%?');
	const [preview, setPreview] = useState<StressScenarioPreview | null>(null);
	const [confirmed, setConfirmed] = useState(false);
	const [name, setName] = useState('Market drawdown scenario');
	const [description, setDescription] = useState('Broad market decline with higher volatility.');
	const [marketShock, setMarketShock] = useState(-20);
	const [volatilityShock, setVolatilityShock] = useState(25);
	const [tickerShocks, setTickerShocks] = useState<Record<string, number>>({});
	const [result, setResult] = useState<StressScenarioResult | null>(null);
	const currency = summary.data?.base_currency ?? 'INR';

	const parseScenario = async () => {
		try {
			const next = await stress.parse.mutateAsync(prompt);
			setPreview(next);
			setName(next.name);
			setDescription(next.prompt);
			setMarketShock(next.market_shock);
			setVolatilityShock(next.volatility_shock);
			setTickerShocks(next.ticker_shocks);
			setConfirmed(false);
			setResult(null);
		} catch (error) {
			toast.error(errorMessage(error));
		}
	};

	const updateManualScenario = (update: () => void) => {
		update();
		setPreview(null);
		setConfirmed(false);
		setTickerShocks({});
		setResult(null);
	};

	const runScenario = async () => {
		try {
			const next = await stress.run.mutateAsync({
				name: name.trim() || 'Untitled stress scenario',
				description: description.trim(),
				market_shock: marketShock,
				volatility_shock: volatilityShock,
				ticker_shocks: tickerShocks,
				confirmed: preview ? confirmed : true
			});
			setResult(next);
			toast.success('Stress scenario persisted.');
		} catch (error) {
			toast.error(errorMessage(error));
		}
	};

	const columns: Array<Column<PositionImpact>> = [
		{
			key: 'ticker',
			header: 'Ticker',
			cell: (row) => <span className="font-medium">{row.ticker}</span>
		},
		{
			key: 'shock',
			header: 'Applied shock',
			align: 'right',
			cell: (row) => formatPercent(row.applied_shock / 100)
		},
		{
			key: 'before',
			header: 'Before',
			align: 'right',
			cell: (row) => formatCurrency(row.value_before, currency)
		},
		{
			key: 'after',
			header: 'After',
			align: 'right',
			cell: (row) => formatCurrency(row.value_after, currency)
		},
		{
			key: 'impact',
			header: 'Impact',
			align: 'right',
			cell: (row) => (
				<span className={row.impact < 0 ? 'text-negative' : 'text-positive'}>
					{formatCurrency(row.impact, currency)}
				</span>
			)
		}
	];

	return (
		<div className="space-y-4">
			<PageHeader
				title="Stress Tests"
				description="Translate plain-language market assumptions into an auditable portfolio impact scenario."
				actions={
					<Button size="sm" variant="outline" onClick={() => void summary.refetch()}>
						<RefreshCw className="size-3.5" /> Refresh value
					</Button>
				}
			/>

			<SectionCard
				title="Describe a scenario"
				description="Latent extracts market, volatility, and holding-specific shocks. Nothing runs until you review the assumptions."
			>
				<div className="flex flex-col gap-2 sm:flex-row">
					<Textarea
						value={prompt}
						onChange={(event) => setPrompt(event.target.value)}
						className="min-h-20 min-w-0"
						placeholder="Example: NIFTY falls 12%, VIX rises 35%, and INFY falls 20%."
					/>
					<Button
						className="self-end"
						onClick={() => void parseScenario()}
						disabled={stress.parse.isPending || prompt.trim().length < 3}
					>
						{stress.parse.isPending ? (
							<LoaderCircle className="size-4 animate-spin" />
						) : (
							<Sparkles className="size-4" />
						)}{' '}
						Interpret
					</Button>
				</div>
				{preview ? (
					<div className="bg-surface-strong/35 mt-4 rounded-lg border p-4">
						<div className="flex flex-wrap items-center justify-between gap-2">
							<p className="text-sm font-semibold">Review interpreted assumptions</p>
							<Badge variant="outline">Confirmation required</Badge>
						</div>
						<ul className="text-muted-foreground mt-3 space-y-1 text-sm">
							{preview.assumptions.map((item) => (
								<li key={item}>• {item}</li>
							))}
						</ul>
						<div className="mt-4 flex items-center gap-2">
							<Checkbox
								id="confirm-scenario"
								checked={confirmed}
								onCheckedChange={(value) => setConfirmed(value === true)}
							/>
							<Label htmlFor="confirm-scenario" className="font-normal">
								I reviewed these assumptions and want to run this scenario.
							</Label>
						</div>
					</div>
				) : null}
			</SectionCard>

			<SectionCard
				title="Scenario controls"
				description="Adjusting a control switches back to a manual scenario."
			>
				{summary.isError ? (
					<div className="mb-4">
						<ErrorState error={summary.error} onRetry={() => void summary.refetch()} />
					</div>
				) : null}
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
								onValueChange={([value]) =>
									updateManualScenario(() => setMarketShock(value ?? -20))
								}
							/>
						</div>
						<div className="grid gap-2">
							<Label>
								Volatility shock: {volatilityShock >= 0 ? '+' : ''}
								{volatilityShock}%
							</Label>
							<Slider
								value={[volatilityShock]}
								min={-50}
								max={150}
								step={5}
								onValueChange={([value]) =>
									updateManualScenario(() => setVolatilityShock(value ?? 25))
								}
							/>
						</div>
					</div>
				</div>
				<div className="mt-4 flex flex-wrap gap-2">
					<Button
						disabled={
							summary.isLoading ||
							summary.isError ||
							stress.run.isPending ||
							Boolean(preview && !confirmed)
						}
						onClick={() => void runScenario()}
					>
						{stress.run.isPending ? (
							<LoaderCircle className="size-4 animate-spin" />
						) : (
							<Play className="size-4" />
						)}{' '}
						Run scenario
					</Button>
					<Button variant="outline" disabled={!result} onClick={() => result && download(result)}>
						<Download className="size-4" /> Export JSON
					</Button>
				</div>
			</SectionCard>

			<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
				<MetricCard
					label="Value before"
					value={formatCurrency(result?.value_before ?? summary.data?.current_value, currency)}
					loading={summary.isLoading}
					explanation={{ portfolioId, metric: 'portfolio_value' }}
				/>
				<MetricCard
					label="Value after"
					value={formatCurrency(result?.value_after, currency)}
					tone={result && result.value_after >= result.value_before ? 'positive' : 'negative'}
				/>
				<MetricCard
					label="Estimated impact"
					value={formatCurrency(result?.estimated_impact, currency)}
					hint={result ? formatPercent(result.estimated_impact_pct) : undefined}
					tone={result && result.estimated_impact >= 0 ? 'positive' : 'negative'}
				/>
				<MetricCard
					label="Stressed historical VaR"
					value={formatPercent(result?.historical_var_after)}
					hint={result ? `Base ${formatPercent(result.historical_var_before)}` : undefined}
					explanation={{ portfolioId, metric: 'historical_var' }}
				/>
			</div>

			<SectionCard
				title="Position impact"
				description="Attribution uses each current market value and any ticker-specific shock before the broad market assumption."
			>
				{result?.position_impacts.length ? (
					<DataTable
						dense
						columns={columns}
						rows={result.position_impacts}
						rowKey={(row) => row.ticker}
					/>
				) : (
					<EmptyState title="Run a scenario to see position attribution" />
				)}
			</SectionCard>

			{result ? (
				<SectionCard title="Method and assumptions">
					<ul className="text-muted-foreground space-y-1 text-sm">
						{result.assumptions.map((item) => (
							<li key={item}>• {item}</li>
						))}
					</ul>
					<p className="text-muted-foreground mt-3 text-xs">
						This is a sensitivity estimate, not a forecast or investment recommendation.
					</p>
				</SectionCard>
			) : null}
		</div>
	);
}

function download(result: StressScenarioResult) {
	const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
	const url = URL.createObjectURL(blob);
	const link = document.createElement('a');
	link.href = url;
	link.download = `${result.name.toLowerCase().replace(/\s+/g, '-')}.json`;
	link.click();
	URL.revokeObjectURL(url);
}
