'use client';

import { ArrowRight, Check, Eye, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';
import { toast } from 'sonner';

import { EmptyState, ErrorState, MetricGridSkeleton } from '@/components/common/states';
import { CategoryBadge, SeverityBadge } from '@/components/domain/finance';
import { RequirePortfolio } from '@/components/layout/require-portfolio';
import { PageHeader } from '@/components/layout/top-bar';
import {
	Accordion,
	AccordionContent,
	AccordionItem,
	AccordionTrigger
} from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { errorMessage } from '@/lib/api';
import { formatDate } from '@/lib/format';
import { useAlerts, useRecommendations } from '@/lib/queries';
import type { IntelligenceRecommendation, PortfolioAlert } from '@/lib/types';

export default function RecommendationsRoutePage() {
	return (
		<RequirePortfolio label="recommendations">
			{(id) => <RecommendationCenter portfolioId={id} />}
		</RequirePortfolio>
	);
}

function RecommendationCenter({ portfolioId }: { portfolioId: string }) {
	const recommendations = useRecommendations(portfolioId);
	const alerts = useAlerts(portfolioId);
	const [severity, setSeverity] = useState('all');
	const [category, setCategory] = useState('all');
	const rows = recommendations.data ?? [];
	const categories = [...new Set(rows.map((item) => item.category))].sort();
	const filtered = rows.filter(
		(item) =>
			(severity === 'all' || item.severity === severity) &&
			(category === 'all' || item.category === category)
	);

	const markRecommendation = async (item: IntelligenceRecommendation) => {
		try {
			await recommendations.setRead.mutateAsync({ id: item.id, isRead: !item.is_read });
		} catch (error) {
			toast.error(errorMessage(error));
		}
	};

	const markAlert = async (item: PortfolioAlert) => {
		try {
			await alerts.setRead.mutateAsync({ id: item.id, isRead: !item.is_read });
		} catch (error) {
			toast.error(errorMessage(error));
		}
	};

	return (
		<div className="space-y-4">
			<PageHeader
				title="Recommendations"
				description="A focused review list, ordered by priority. Expand an item to see the evidence and next step."
				actions={
					<Button
						size="sm"
						variant="outline"
						onClick={() => {
							void recommendations.refetch();
							void alerts.refetch();
						}}
					>
						<RefreshCw className="size-3.5" /> Refresh evidence
					</Button>
				}
			/>

			{recommendations.isLoading ? (
				<MetricGridSkeleton count={4} />
			) : (
				<dl className="grid grid-cols-3 gap-4 border-b py-4">
					{[
						[
							'To review',
							recommendations.isError ? '—' : rows.filter((item) => !item.is_read).length
						],
						[
							'High priority',
							recommendations.isError ? '—' : rows.filter((item) => item.severity === 'high').length
						],
						[
							'Unread alerts',
							alerts.isError || alerts.isLoading
								? '—'
								: (alerts.data ?? []).filter((item) => !item.is_read).length
						]
					].map(([label, count]) => (
						<div key={String(label)} className="space-y-1">
							<dt className="text-muted-foreground text-xs">{label}</dt>
							<dd className="num text-2xl font-medium">{count}</dd>
						</div>
					))}
				</dl>
			)}

			<p className="text-muted-foreground text-xs">
				Based on portfolio rules and available data, not predictions or instructions to trade.
			</p>
			<Tabs defaultValue="actions">
				<TabsList>
					<TabsTrigger value="actions">Actions</TabsTrigger>
					<TabsTrigger value="alerts">Alerts</TabsTrigger>
				</TabsList>
				<TabsContent value="actions" className="mt-4 space-y-4">
					<div className="flex flex-wrap gap-2">
						<Select value={severity} onValueChange={setSeverity}>
							<SelectTrigger aria-label="Filter by priority" className="w-[10rem]">
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="all">All priorities</SelectItem>
								<SelectItem value="high">High</SelectItem>
								<SelectItem value="medium">Medium</SelectItem>
								<SelectItem value="low">Low</SelectItem>
							</SelectContent>
						</Select>
						<Select value={category} onValueChange={setCategory}>
							<SelectTrigger aria-label="Filter by category" className="w-[12rem]">
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="all">All categories</SelectItem>
								{categories.map((item) => (
									<SelectItem key={item} value={item}>
										{item}
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					</div>
					{recommendations.isError ? (
						<ErrorState
							error={recommendations.error}
							onRetry={() => void recommendations.refetch()}
						/>
					) : recommendations.isLoading ? (
						<MetricGridSkeleton count={2} />
					) : filtered.length ? (
						<Accordion
							type="single"
							collapsible
							defaultValue={String(filtered[0]?.id)}
							className="border-t"
						>
							{filtered.map((item) => (
								<RecommendationCard
									key={item.id}
									item={item}
									onMark={() => void markRecommendation(item)}
								/>
							))}
						</Accordion>
					) : (
						<EmptyState
							title="No matching recommendations"
							description="The current evidence does not trigger an action in this filter."
						/>
					)}
				</TabsContent>

				<TabsContent value="alerts" className="mt-4">
					{alerts.isError ? (
						<ErrorState error={alerts.error} onRetry={() => void alerts.refetch()} />
					) : alerts.data?.length ? (
						<div className="grid gap-3 lg:grid-cols-2">
							{alerts.data.map((item) => (
								<Card key={item.id} className="panel-surface gap-3 p-4">
									<div className="flex flex-wrap items-center justify-between gap-2">
										<div className="flex items-center gap-2">
											<SeverityBadge severity={item.severity} />
											<Badge variant="outline">{item.alert_type.replaceAll('_', ' ')}</Badge>
										</div>
										<span className="text-muted-foreground text-xs">
											{formatDate(item.detected_at)}
										</span>
									</div>
									<div>
										<p className="font-medium">{item.title}</p>
										<p className="text-muted-foreground mt-1 text-sm leading-6">
											{item.description}
										</p>
									</div>
									{item.evidence ? (
										<p className="bg-surface-strong/45 rounded-md border p-2.5 text-xs">
											<span className="text-muted-foreground">Evidence: </span>
											{item.evidence}
										</p>
									) : null}
									<Button
										size="sm"
										variant="ghost"
										className="self-start"
										onClick={() => void markAlert(item)}
									>
										{item.is_read ? <Eye className="size-3.5" /> : <Check className="size-3.5" />}
										{item.is_read ? 'Mark unread' : 'Mark read'}
									</Button>
								</Card>
							))}
						</div>
					) : (
						<EmptyState
							title="No active alerts"
							description="New data quality and material risk signals will appear here."
						/>
					)}
				</TabsContent>
			</Tabs>
		</div>
	);
}

function RecommendationCard({
	item,
	onMark
}: {
	item: IntelligenceRecommendation;
	onMark: () => void;
}) {
	const prompt = `Explain recommendation: ${item.title}. Use its evidence and tell me what to review before acting.`;
	return (
		<AccordionItem value={String(item.id)} className="border-b">
			<AccordionTrigger className="gap-4 py-5 text-left hover:no-underline">
				<span className="flex min-w-0 flex-1 flex-col gap-2">
					<span className="flex flex-wrap items-center gap-2">
						<SeverityBadge severity={item.severity} />
						<CategoryBadge category={item.category} />
						{item.is_read ? <Badge variant="outline">Reviewed</Badge> : null}
					</span>
					<span className="text-base font-medium">{item.title}</span>
					<span className="text-muted-foreground text-sm font-normal">{item.evidence}</span>
				</span>
			</AccordionTrigger>
			<AccordionContent className="pb-5">
				<div className="grid gap-5 md:grid-cols-2">
					<div className="space-y-2">
						<p className="text-muted-foreground text-xs">WHY IT MATTERS</p>
						<p className="text-sm leading-6">{item.description}</p>
						<p className="text-muted-foreground text-xs leading-5">{item.expected_impact}</p>
					</div>
					<div className="space-y-2 md:border-l md:pl-5">
						<p className="text-muted-foreground text-xs">WHAT TO REVIEW</p>
						<p className="text-sm leading-6">{item.action}</p>
					</div>
				</div>
				<div className="mt-4 flex flex-wrap gap-2">
					<Button size="sm" variant="outline" onClick={onMark}>
						{item.is_read ? <Eye className="size-3.5" /> : <Check className="size-3.5" />}
						{item.is_read ? 'Mark unread' : 'Mark read'}
					</Button>
					<Button asChild size="sm" variant="ghost">
						<Link href={`/ai-copilot?prompt=${encodeURIComponent(prompt)}`}>
							Ask Copilot <ArrowRight className="size-3.5" />
						</Link>
					</Button>
				</div>
			</AccordionContent>
		</AccordionItem>
	);
}
