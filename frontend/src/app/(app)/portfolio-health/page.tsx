'use client';

import { ArrowRight, CheckCircle2, TriangleAlert } from 'lucide-react';
import Link from 'next/link';

import { ChartCard, SectionCard } from '@/components/charts/chart-card';
import { CategoryBadge, RegimeBadge, SeverityBadge } from '@/components/domain/finance';
import { MetricCard } from '@/components/common/metric-card';
import { RequirePortfolio } from '@/components/layout/require-portfolio';
import { SeriesLineChart } from '@/components/charts/series-charts';
import { EmptyState } from '@/components/common/states';
import { PageHeader } from '@/components/layout/top-bar';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { buildHealthReport } from '@/lib/analytics-derive';
import { usePositions, useRegime, useRisk, useSummary } from '@/lib/queries';

export default function PortfolioHealthRoutePage() {
	return (
		<RequirePortfolio label="the health score">
			{(id) => <HealthPage portfolioId={id} />}
		</RequirePortfolio>
	);
}

function HealthPage({ portfolioId }: { portfolioId: string }) {
	const summary = useSummary(portfolioId);
	const positions = usePositions(portfolioId);
	const risk = useRisk(portfolioId);
	const regime = useRegime(portfolioId);

	const report = buildHealthReport({
		summary: summary.data,
		positions: positions.data ?? [],
		risk: risk.data,
		regime: regime.data
	});

	const tone = report.score >= 75 ? 'positive' : report.score >= 50 ? 'warning' : 'negative';
	const barClass =
		report.score >= 75 ? 'bg-positive' : report.score >= 50 ? 'bg-warning' : 'bg-negative';

	return (
		<div className="space-y-4">
			<PageHeader
				title="Portfolio Health"
				description="A weighted composite of return, risk, diversification, regime, and data quality."
				actions={
					<Button size="sm" variant="outline" asChild>
						<Link href="/recommendations">
							Recommendations <ArrowRight className="size-3.5" />
						</Link>
					</Button>
				}
			/>

			<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
				<MetricCard
					label="Health score"
					value={`${report.score}/100`}
					tone={tone}
					hint={report.category}
					loading={risk.isLoading}
				/>
				<MetricCard label="Risk category" value={report.category} tone={tone} />
				<MetricCard
					label="Trend"
					value={report.trend}
					tone={
						report.trend === 'Improving'
							? 'positive'
							: report.trend === 'Deteriorating'
								? 'negative'
								: 'neutral'
					}
				/>
				<MetricCard
					label="Regime backdrop"
					value={<RegimeBadge label={regime.data?.current_regime} size="lg" />}
					loading={regime.isLoading}
				/>
			</div>

			<SectionCard title="Score components">
				<div className="space-y-3">
					{report.components.map((component) => (
						<div key={component.key} className="space-y-1.5">
							<div className="flex flex-wrap items-baseline justify-between gap-2">
								<span className="text-sm font-medium">{component.label}</span>
								<span className="text-muted-foreground num text-xs">
									{component.score}/100 · weight {(component.weight * 100).toFixed(0)}%
								</span>
							</div>
							<Progress
								value={component.score}
								className="h-2"
								indicatorClassName={
									component.score >= 70
										? 'bg-positive'
										: component.score >= 45
											? 'bg-warning'
											: 'bg-negative'
								}
							/>
							<p className="text-muted-foreground text-xs">{component.detail}</p>
						</div>
					))}
				</div>
				<div className="mt-4 space-y-1.5 border-t pt-4">
					<div className="flex items-baseline justify-between">
						<span className="text-sm font-semibold">Composite score</span>
						<span className="num text-sm font-semibold">{report.score}/100</span>
					</div>
					<Progress value={report.score} className="h-2.5" indicatorClassName={barClass} />
				</div>
			</SectionCard>

			<div className="grid gap-4 lg:grid-cols-2">
				<SectionCard title="Strengths">
					{report.strengths.length === 0 ? (
						<EmptyState title="No standout strengths yet" />
					) : (
						<ul className="space-y-2 text-sm">
							{report.strengths.map((item) => (
								<li key={item} className="flex items-start gap-2">
									<CheckCircle2 className="text-positive mt-0.5 size-4 shrink-0" />
									{item}
								</li>
							))}
						</ul>
					)}
				</SectionCard>
				<SectionCard title="Weaknesses">
					{report.weaknesses.length === 0 ? (
						<EmptyState title="No material weaknesses detected" />
					) : (
						<ul className="space-y-2 text-sm">
							{report.weaknesses.map((item) => (
								<li key={item} className="flex items-start gap-2">
									<TriangleAlert className="text-warning mt-0.5 size-4 shrink-0" />
									{item}
								</li>
							))}
						</ul>
					)}
				</SectionCard>
			</div>

			<ChartCard title="Health trajectory">
				{report.history.length ? (
					<SeriesLineChart data={report.history} percent={false} color="var(--chart-2)" />
				) : (
					<EmptyState title="Not enough history" />
				)}
			</ChartCard>

			<SectionCard title="Risk drivers">
				{report.drivers.length === 0 ? (
					<EmptyState title="No active risk drivers" />
				) : (
					<div className="grid gap-3 md:grid-cols-2">
						{report.drivers.map((driver) => (
							<div key={driver.id} className="rounded-lg border p-3">
								<div className="flex flex-wrap items-center gap-2">
									<SeverityBadge severity={driver.severity} />
									<CategoryBadge category={driver.category} />
								</div>
								<p className="mt-2 text-sm font-medium">{driver.title}</p>
								<p className="text-muted-foreground mt-1 text-xs">{driver.description}</p>
								<p className="num mt-2 text-xs font-medium">{driver.metric}</p>
								<p className="text-muted-foreground mt-1 text-xs">{driver.action}</p>
							</div>
						))}
					</div>
				)}
			</SectionCard>
		</div>
	);
}
