'use client';

import { ArrowRight, Bell, Check, Eye, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';
import { toast } from 'sonner';

import { MetricCard } from '@/components/common/metric-card';
import { EmptyState, ErrorState, MetricGridSkeleton } from '@/components/common/states';
import { CategoryBadge, SeverityBadge } from '@/components/domain/finance';
import { RequirePortfolio } from '@/components/layout/require-portfolio';
import { PageHeader } from '@/components/layout/top-bar';
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
import { formatDate, formatPercent } from '@/lib/format';
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
				description="Evidence-led actions generated from the same portfolio, risk, regime, and profile data used across Latent."
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
				<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
					<MetricCard label="Total actions" value={rows.length} />
					<MetricCard
						label="High priority"
						value={rows.filter((item) => item.severity === 'high').length}
						tone="negative"
					/>
					<MetricCard label="Unread" value={rows.filter((item) => !item.is_read).length} />
					<MetricCard
						label="Active alerts"
						value={(alerts.data ?? []).filter((item) => !item.is_read).length}
						icon={<Bell className="size-4" />}
					/>
				</div>
			)}

			<Tabs defaultValue="actions">
				<TabsList>
					<TabsTrigger value="actions">Actions</TabsTrigger>
					<TabsTrigger value="alerts">Alerts</TabsTrigger>
				</TabsList>
				<TabsContent value="actions" className="mt-4 space-y-4">
					<div className="flex flex-wrap gap-2">
						<Select value={severity} onValueChange={setSeverity}>
							<SelectTrigger className="w-[10rem]">
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
							<SelectTrigger className="w-[12rem]">
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
					) : filtered.length ? (
						<div className="grid gap-3 lg:grid-cols-2">
							{filtered.map((item) => (
								<RecommendationCard
									key={item.id}
									item={item}
									onMark={() => void markRecommendation(item)}
								/>
							))}
						</div>
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
		<Card className="panel-surface gap-4 p-4">
			<div className="flex flex-wrap items-center justify-between gap-2">
				<div className="flex flex-wrap gap-2">
					<SeverityBadge severity={item.severity} />
					<CategoryBadge category={item.category} />
					{item.is_read ? <Badge variant="secondary">Read</Badge> : null}
				</div>
				<span className="num text-muted-foreground text-xs">
					{formatPercent(item.confidence)} rule confidence
				</span>
			</div>
			<div>
				<p className="font-medium">{item.title}</p>
				<p className="text-muted-foreground mt-1 text-sm leading-6">{item.description}</p>
			</div>
			<div className="grid gap-2 text-sm sm:grid-cols-2">
				<div className="bg-surface-strong/40 rounded-md border p-3">
					<p className="text-muted-foreground text-xs font-medium uppercase">Evidence</p>
					<p className="mt-1.5 leading-5">{item.evidence}</p>
				</div>
				<div className="bg-surface-strong/40 rounded-md border p-3">
					<p className="text-muted-foreground text-xs font-medium uppercase">Action</p>
					<p className="mt-1.5 leading-5">{item.action}</p>
				</div>
			</div>
			<p className="text-muted-foreground text-xs">Expected effect: {item.expected_impact}</p>
			<div className="flex flex-wrap gap-2">
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
		</Card>
	);
}
