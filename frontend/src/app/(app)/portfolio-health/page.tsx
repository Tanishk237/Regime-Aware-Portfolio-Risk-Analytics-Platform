'use client';

import Link from 'next/link';
import { ArrowRight, RefreshCw } from 'lucide-react';
import { SectionCard } from '@/components/charts/chart-card';
import { EmptyState, ErrorState, LoadingSkeleton, WarningState } from '@/components/common/states';
import { RequirePortfolio } from '@/components/layout/require-portfolio';
import { PageHeader } from '@/components/layout/top-bar';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useIntelligence } from '@/lib/api/intelligence';
import { formatDate, formatPercent, formatRisk } from '@/lib/format';

export default function PortfolioHealthRoutePage() {
	return (
		<RequirePortfolio label="risk review">
			{(id) => <HealthPage key={id} portfolioId={id} />}
		</RequirePortfolio>
	);
}

function HealthPage({ portfolioId }: { portfolioId: string }) {
	const intelligence = useIntelligence(portfolioId);
	const risk = intelligence.data?.risk;
	const report = risk?.review;
	const period = risk?.methodology;
	return (
		<div className="space-y-6">
			<PageHeader
				title="Risk review"
				description="Understand the evidence behind your score, before making a decision."
				actions={
					<Button
						size="sm"
						variant="outline"
						onClick={() => void intelligence.refetch()}
						disabled={intelligence.isFetching}
					>
						<RefreshCw className="size-4" /> Refresh
					</Button>
				}
			/>
			{intelligence.isError ? (
				<ErrorState error={intelligence.error} onRetry={() => void intelligence.refetch()} />
			) : null}
			{intelligence.isLoading ? (
				<LoadingSkeleton rows={6} />
			) : !report ? (
				<EmptyState
					title="Risk review is unavailable"
					description="Add holdings and market history, then retry. Missing evidence is not a sign of low risk."
				/>
			) : (
				<>
					<section className="grid gap-6 border-b pb-6 md:grid-cols-[14rem_minmax(0,1fr)]">
						<div>
							<p className="text-muted-foreground text-sm">Risk-review score</p>
							<p className="num my-3 text-4xl font-medium">
								{report.score == null ? (
									'Unavailable'
								) : (
									<>
										{report.score}
										<span className="text-muted-foreground text-xl"> / 100</span>
									</>
								)}
							</p>
							<Badge variant="outline">{report.category}</Badge>
							{report.score != null ? (
								<Progress className="mt-4" value={report.score} aria-label="Risk-review score" />
							) : null}
						</div>
						<div className="space-y-3 text-sm leading-6">
							<h2 className="text-base font-medium">A review aid, not a safety rating</h2>
							<p className="text-muted-foreground">{report.limitation}</p>
							<p>
								{period
									? `${formatDate(period.start_date)} to ${formatDate(period.end_date)}`
									: 'Period unavailable'}{' '}
								· {report.observation_count} daily observations
							</p>
							<p className="text-muted-foreground">
								The dashboard and this page use the same backend calculation. No estimated
								historical score is shown.
							</p>
						</div>
					</section>
					{report.missing_inputs.length ? (
						<WarningState
							title="A score cannot be calculated yet"
							description={`Missing: ${report.missing_inputs.join(', ')}. Available inputs are shown below without filling in unknown values.`}
						/>
					) : null}
					<SectionCard
						title="How it is calculated"
						description={`Starts at 100, applies the contributions below, then rounds within 0–100. Formula: ${report.calculation_version}.`}
					>
						<div className="divide-y">
							{report.components.map((item) => (
								<div
									key={item.key}
									className="grid gap-2 py-4 first:pt-0 last:pb-0 sm:grid-cols-[minmax(0,1fr)_7rem]"
								>
									<div>
										<h3 className="text-sm font-medium">
											{item.label} ·{' '}
											<span className="num">
												{item.key === 'sharpe' ? formatRisk(item.value) : formatPercent(item.value)}
											</span>
										</h3>
										<p className="text-muted-foreground mt-1 text-sm">{item.rule}</p>
									</div>
									<p className="num text-sm sm:text-right">
										{item.points > 0 ? '+' : ''}
										{item.points.toFixed(1)} points
									</p>
								</div>
							))}
						</div>
					</SectionCard>
					<section className="space-y-3">
						<h2 className="text-base font-medium">What the score does not cover</h2>
						<p className="text-muted-foreground max-w-3xl text-sm leading-6">
							A high score can still hide heavy exposure to one sector or stock. Check
							concentration, your need for cash, and the age of prices. Market-state estimates do
							not add bonus points.
						</p>
						<div className="flex flex-wrap gap-2">
							<Button asChild variant="outline">
								<Link href="/dashboard">
									Review allocation <ArrowRight className="size-4" />
								</Link>
							</Button>
							<Button asChild>
								<Link href="/recommendations">
									Review recommendations <ArrowRight className="size-4" />
								</Link>
							</Button>
						</div>
					</section>
				</>
			)}
		</div>
	);
}
