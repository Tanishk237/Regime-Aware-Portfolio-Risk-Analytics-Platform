'use client';

import { RefreshCw, Search } from 'lucide-react';
import { useState } from 'react';

import { ChartCard, SectionCard } from '@/components/charts/chart-card';
import { DataTable, type Column } from '@/components/common/data-table';
import { DateRangeControls } from '@/components/common/date-range-controls';
import { MetricCard } from '@/components/common/metric-card';
import { SeriesLineChart } from '@/components/charts/series-charts';
import { EmptyState, ErrorState, LoadingSkeleton } from '@/components/common/states';
import { PageHeader } from '@/components/layout/top-bar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { daysAgo, formatCurrency, formatDate, formatNumber, isoDate, toSeries } from '@/lib/format';
import { useMarketSnapshot } from '@/lib/queries';
import type { FiiDiiFlowPoint, HistoricalPricePoint, VixPoint } from '@/lib/types';

export default function MarketPage() {
	const [ticker, setTicker] = useState('RELIANCE.NS');
	const [query, setQuery] = useState('RELIANCE.NS');
	const [indexSymbol, setIndexSymbol] = useState('^NSEI');
	const [startDate, setStartDate] = useState(daysAgo(365));
	const [endDate, setEndDate] = useState(isoDate(new Date()));

	const market = useMarketSnapshot({
		tickers: [query],
		index_symbol: indexSymbol,
		start_date: startDate,
		end_date: endDate,
		include_features: true
	});

	const priceRows = market.data?.historical_prices ?? [];
	const closeSeries = toSeries(
		priceRows
			.filter((row) => row.close !== undefined && row.date)
			.map((row) => ({ date: String(row.date), value: Number(row.close) }))
	);
	const latest = priceRows.at(-1);
	const first = priceRows[0];
	const change =
		latest?.close !== undefined && first?.close
			? (Number(latest.close) - Number(first.close)) / Number(first.close)
			: undefined;
	const live = market.data?.live_prices?.[0];
	const latestVix = market.data?.vix?.at(-1);
	const latestFlow = market.data?.fii_dii_flows?.at(-1);

	const priceColumns: Array<Column<HistoricalPricePoint>> = [
		{
			key: 'date',
			header: 'Date',
			cell: (row) => <span className="num">{formatDate(row.date)}</span>
		},
		{
			key: 'open',
			header: 'Open',
			align: 'right',
			cell: (row) => <span className="num">{formatNumber(row.open)}</span>
		},
		{
			key: 'high',
			header: 'High',
			align: 'right',
			cell: (row) => <span className="num">{formatNumber(row.high)}</span>
		},
		{
			key: 'low',
			header: 'Low',
			align: 'right',
			cell: (row) => <span className="num">{formatNumber(row.low)}</span>
		},
		{
			key: 'close',
			header: 'Close',
			align: 'right',
			cell: (row) => <span className="num font-medium">{formatNumber(row.close)}</span>
		},
		{
			key: 'volume',
			header: 'Volume',
			align: 'right',
			cell: (row) => <span className="num">{formatNumber(row.volume, 0)}</span>
		}
	];

	const flowColumns: Array<Column<FiiDiiFlowPoint>> = [
		{
			key: 'date',
			header: 'Date',
			cell: (row) => <span className="num">{formatDate(row.date)}</span>
		},
		{
			key: 'fii',
			header: 'FII',
			align: 'right',
			cell: (row) => <span className="num">{formatCurrency(row.fii, 'INR', true)}</span>
		},
		{
			key: 'dii',
			header: 'DII',
			align: 'right',
			cell: (row) => <span className="num">{formatCurrency(row.dii, 'INR', true)}</span>
		},
		{
			key: 'net',
			header: 'Net flow',
			align: 'right',
			cell: (row) => <span className="num">{formatCurrency(row.net_flow, 'INR', true)}</span>
		}
	];

	const vixColumns: Array<Column<VixPoint>> = [
		{
			key: 'date',
			header: 'Date',
			cell: (row) => <span className="num">{formatDate(row.date)}</span>
		},
		{ key: 'vix', header: 'VIX', align: 'right', cell: (row) => formatNumber(row.vix) },
		{
			key: 'change',
			header: 'Change',
			align: 'right',
			cell: (row) => formatNumber(row.vix_change)
		}
	];

	return (
		<div className="space-y-4">
			<PageHeader
				title="Market Data"
				description="Historical prices, live prices, India VIX, FII/DII flows, index data, and features."
				actions={
					<Button size="sm" variant="outline" onClick={() => void market.refetch()}>
						<RefreshCw className="size-3.5" /> Refresh
					</Button>
				}
			/>

			<SectionCard title="Query">
				<div className="flex flex-wrap items-end gap-3">
					<div className="grid gap-1.5">
						<Label htmlFor="ticker" className="text-muted-foreground text-xs">
							Ticker
						</Label>
						<Input
							id="ticker"
							value={ticker}
							onChange={(event) => setTicker(event.target.value.toUpperCase())}
							className="h-9 w-[12rem]"
							placeholder="RELIANCE.NS"
						/>
					</div>
					<div className="grid gap-1.5">
						<Label htmlFor="index" className="text-muted-foreground text-xs">
							Index
						</Label>
						<Input
							id="index"
							value={indexSymbol}
							onChange={(event) => setIndexSymbol(event.target.value.toUpperCase())}
							className="h-9 w-[8rem]"
							placeholder="^NSEI"
						/>
					</div>
					<DateRangeControls
						startDate={startDate}
						endDate={endDate}
						onStartDate={setStartDate}
						onEndDate={setEndDate}
					/>
					<Button size="sm" onClick={() => setQuery(ticker.trim().toUpperCase())}>
						<Search className="size-3.5" /> Fetch
					</Button>
				</div>
			</SectionCard>

			<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
				<MetricCard label="Symbol" value={query || '-'} hint={`${priceRows.length} bars`} />
				<MetricCard
					label="Live price"
					value={formatNumber(live?.price ?? latest?.close)}
					loading={market.isLoading}
					hint={live?.name ?? (latest?.date ? formatDate(latest.date) : undefined)}
				/>
				<MetricCard
					label="Window change"
					value={change === undefined ? '-' : `${(change * 100).toFixed(2)}%`}
					tone={change === undefined ? 'neutral' : change >= 0 ? 'positive' : 'negative'}
					loading={market.isLoading}
				/>
				<MetricCard
					label="India VIX"
					value={formatNumber(latestVix?.vix)}
					loading={market.isLoading}
					hint={latestVix?.date ? formatDate(latestVix.date) : undefined}
				/>
			</div>

			<ChartCard title="Close price" description={`${query} · ${startDate} to ${endDate}`}>
				{market.isLoading ? (
					<LoadingSkeleton rows={5} />
				) : market.isError ? (
					<ErrorState error={market.error} onRetry={() => void market.refetch()} />
				) : closeSeries.length === 0 ? (
					<EmptyState title="No market data returned" />
				) : (
					<SeriesLineChart data={closeSeries} percent={false} color="var(--chart-2)" height={280} />
				)}
			</ChartCard>

			<Tabs defaultValue="prices">
				<TabsList>
					<TabsTrigger value="prices">OHLCV</TabsTrigger>
					<TabsTrigger value="flows">FII / DII</TabsTrigger>
					<TabsTrigger value="vix">India VIX</TabsTrigger>
					<TabsTrigger value="features">Features</TabsTrigger>
				</TabsList>
				<TabsContent value="prices" className="mt-3">
					<DataTable
						columns={priceColumns}
						rows={priceRows.slice(-60).reverse()}
						rowKey={(row, index) => `${row.date}-${index}`}
						empty={<EmptyState title="No price rows" />}
						dense
					/>
				</TabsContent>
				<TabsContent value="flows" className="mt-3">
					<DataTable
						columns={flowColumns}
						rows={(market.data?.fii_dii_flows ?? []).slice(-60).reverse()}
						rowKey={(row, index) => `${row.date}-${index}`}
						empty={<EmptyState title="FII/DII data unavailable" />}
						dense
					/>
					<p className="text-muted-foreground mt-2 text-xs">
						Latest net flow {formatCurrency(latestFlow?.net_flow, 'INR', true)}
					</p>
				</TabsContent>
				<TabsContent value="vix" className="mt-3">
					<DataTable
						columns={vixColumns}
						rows={(market.data?.vix ?? []).slice(-60).reverse()}
						rowKey={(row, index) => `${row.date}-${index}`}
						empty={<EmptyState title="India VIX data unavailable" />}
						dense
					/>
				</TabsContent>
				<TabsContent value="features" className="mt-3">
					<SectionCard title="Feature validation">
						{market.data?.features ? (
							<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
								<MetricCard
									label="Valid"
									value={market.data.features.validation.is_valid ? 'Yes' : 'No'}
									tone={market.data.features.validation.is_valid ? 'positive' : 'negative'}
								/>
								<MetricCard label="Rows" value={market.data.features.validation.rows} />
								<MetricCard label="Columns" value={market.data.features.validation.columns} />
								<MetricCard
									label="Missing values"
									value={market.data.features.validation.missing_values}
								/>
							</div>
						) : (
							<EmptyState title="Feature matrix unavailable" />
						)}
					</SectionCard>
				</TabsContent>
			</Tabs>
		</div>
	);
}
