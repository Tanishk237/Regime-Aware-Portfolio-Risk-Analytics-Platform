'use client';

import { Check, Download, Eye, RefreshCw, RotateCcw } from 'lucide-react';
import { useMemo, useState } from 'react';

import { SectionCard } from '@/components/charts/chart-card';
import { CategoryBadge, SeverityBadge, type Severity } from '@/components/domain/finance';
import { MetricCard } from '@/components/common/metric-card';
import { RequirePortfolio } from '@/components/layout/require-portfolio';
import { EmptyState } from '@/components/common/states';
import { PageHeader } from '@/components/layout/top-bar';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
	buildHealthReport,
	buildRecommendations,
	type Recommendation
} from '@/lib/analytics-derive';
import { formatDateTime } from '@/lib/format';
import { usePositions, useRegime, useRisk, useSummary } from '@/lib/queries';

const FILTERS: Array<{ label: string; value: Severity | 'all' }> = [
	{ label: 'All', value: 'all' },
	{ label: 'High', value: 'high' },
	{ label: 'Medium', value: 'medium' },
	{ label: 'Low', value: 'low' }
];

const CATEGORY_FILTERS = [
	'All',
	'Risk',
	'Diversification',
	'Regime',
	'Performance',
	'Data Quality'
];

export default function RecommendationsRoutePage() {
	return (
		<RequirePortfolio label="recommendations">
			{(id) => <RecommendationsPage portfolioId={id} />}
		</RequirePortfolio>
	);
}

function RecommendationsPage({ portfolioId }: { portfolioId: string }) {
	const summary = useSummary(portfolioId);
	const positions = usePositions(portfolioId);
	const risk = useRisk(portfolioId);
	const regime = useRegime(portfolioId);
	const [filter, setFilter] = useState<Severity | 'all'>('all');
	const [category, setCategory] = useState('All');
	const [readIds, setReadIds] = useState<Set<string>>(() => new Set());

	const report = buildHealthReport({
		summary: summary.data,
		positions: positions.data ?? [],
		risk: risk.data,
		regime: regime.data
	});
	const all = buildRecommendations(report);
	const rows = useMemo(
		() =>
			all.filter((item) => {
				const severityMatch = filter === 'all' || item.severity === filter;
				const categoryMatch = category === 'All' || item.category === category;
				return severityMatch && categoryMatch;
			}),
		[all, category, filter]
	);
	const unreadRows = rows.filter((item) => !readIds.has(item.id));
	const readRows = rows.filter((item) => readIds.has(item.id));
	const count = (severity: Severity) => all.filter((item) => item.severity === severity).length;
	const mark = (item: Recommendation, read: boolean) => {
		setReadIds((current) => {
			const next = new Set(current);
			if (read) next.add(item.id);
			else next.delete(item.id);
			return next;
		});
	};

	const exportJson = () => {
		const blob = new Blob([JSON.stringify(all, null, 2)], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const link = document.createElement('a');
		link.href = url;
		link.download = `recommendations-${portfolioId}.json`;
		link.click();
		URL.revokeObjectURL(url);
	};

	return (
		<div className="space-y-4">
			<PageHeader
				title="Recommendations"
				description="Actions ranked by severity, regenerated whenever your analytics change."
				actions={
					<div className="flex gap-2">
						<Button size="sm" variant="outline" onClick={exportJson} disabled={all.length === 0}>
							<Download className="size-3.5" /> Export
						</Button>
						<Button
							size="sm"
							variant="outline"
							onClick={() => {
								void risk.refetch();
								void regime.refetch();
							}}
						>
							<RefreshCw className="size-3.5" /> Regenerate
						</Button>
					</div>
				}
			/>

			<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
				<MetricCard label="Total actions" value={all.length} />
				<MetricCard label="High priority" value={count('high')} tone="negative" />
				<MetricCard label="Medium priority" value={count('medium')} tone="warning" />
				<MetricCard label="Unread" value={all.filter((item) => !readIds.has(item.id)).length} />
			</div>

			<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
				<MetricCard
					label="Health score"
					value={`${report.score}/100`}
					hint={report.category}
					tone={report.score >= 75 ? 'positive' : report.score >= 50 ? 'warning' : 'negative'}
				/>
			</div>

			<div className="space-y-2">
				<div className="flex flex-wrap gap-2">
					{FILTERS.map((item) => (
						<Button
							key={item.value}
							size="sm"
							variant={filter === item.value ? 'default' : 'outline'}
							onClick={() => setFilter(item.value)}
						>
							{item.label}
						</Button>
					))}
				</div>
				<div className="flex flex-wrap gap-2">
					{CATEGORY_FILTERS.map((item) => (
						<Button
							key={item}
							size="sm"
							variant={category === item ? 'secondary' : 'outline'}
							onClick={() => setCategory(item)}
						>
							{item}
						</Button>
					))}
				</div>
			</div>

			<Tabs defaultValue="active">
				<TabsList>
					<TabsTrigger value="active">Active</TabsTrigger>
					<TabsTrigger value="history">History</TabsTrigger>
				</TabsList>
				<TabsContent value="active" className="mt-3">
					<RecommendationList
						rows={unreadRows}
						emptyTitle="No unread recommendations in this view"
						onMark={(item) => mark(item, true)}
						markLabel="Mark read"
						markIcon={<Check className="size-3.5" />}
					/>
				</TabsContent>
				<TabsContent value="history" className="mt-3">
					<RecommendationList
						rows={readRows}
						emptyTitle="No read recommendations yet"
						onMark={(item) => mark(item, false)}
						markLabel="Mark unread"
						markIcon={<RotateCcw className="size-3.5" />}
					/>
				</TabsContent>
			</Tabs>
		</div>
	);
}

function RecommendationList({
	rows,
	emptyTitle,
	onMark,
	markLabel,
	markIcon
}: {
	rows: Recommendation[];
	emptyTitle: string;
	onMark: (item: Recommendation) => void;
	markLabel: string;
	markIcon: React.ReactNode;
}) {
	if (rows.length === 0) return <EmptyState title={emptyTitle} />;

	return (
		<div className="space-y-3">
			{rows.map((item) => (
				<SectionCard
					key={item.id}
					title={item.title}
					description={item.description}
					action={
						<div className="flex flex-wrap items-center gap-2">
							<SeverityBadge severity={item.severity} />
							<CategoryBadge category={item.category} />
							<Button size="sm" variant="outline" onClick={() => onMark(item)}>
								{markIcon} {markLabel}
							</Button>
						</div>
					}
				>
					<div className="grid gap-3 sm:grid-cols-2">
						<div>
							<p className="text-muted-foreground text-xs uppercase">Evidence</p>
							<p className="num mt-1 text-sm font-medium">{item.metric}</p>
						</div>
						<div>
							<p className="text-muted-foreground text-xs uppercase">Suggested action</p>
							<p className="mt-1 text-sm">{item.action}</p>
						</div>
					</div>
					<p className="text-muted-foreground mt-3 inline-flex items-center gap-1 text-xs">
						<Eye className="size-3.5" /> Generated {formatDateTime(item.created_at)}
					</p>
				</SectionCard>
			))}
		</div>
	);
}
