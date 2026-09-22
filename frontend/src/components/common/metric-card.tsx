import { HelpCircle, Loader2, TrendingDown, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import type { ReactNode } from 'react';
import { useState } from 'react';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { useMetricExplanation } from '@/lib/queries';

type MetricCardProps = {
	label: string;
	value: ReactNode;
	hint?: string;
	tooltip?: string;
	delta?: number | null;
	tone?: 'neutral' | 'positive' | 'negative' | 'warning';
	loading?: boolean;
	icon?: ReactNode;
	className?: string;
	explanation?: { portfolioId: string; metric: string };
};

export function MetricCard({
	label,
	value,
	hint,
	tooltip,
	delta,
	tone = 'neutral',
	loading,
	icon,
	className,
	explanation
}: MetricCardProps) {
	const testId = `metric-${label
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/(^-|-$)/g, '')}`;
	const toneClass =
		tone === 'positive'
			? 'text-positive'
			: tone === 'negative'
				? 'text-negative'
				: tone === 'warning'
					? 'text-warning'
					: 'text-foreground';

	const labelNode = tooltip ? (
		<Tooltip>
			<TooltipTrigger asChild>
				<span className="border-border text-muted-foreground cursor-help border-b border-dashed text-xs font-medium uppercase">
					{label}
				</span>
			</TooltipTrigger>
			<TooltipContent className="max-w-[16rem]">{tooltip}</TooltipContent>
		</Tooltip>
	) : (
		<span className="text-muted-foreground text-xs font-medium uppercase">{label}</span>
	);

	return (
		<Card
			data-testid={testId}
			data-interactive="true"
			className={cn(
				'metric-surface panel-surface border-border/70 hover:border-primary/25 group relative min-h-32 gap-0 overflow-hidden p-4',
				className
			)}
		>
			<div className="bg-primary absolute inset-y-4 left-0 w-0.5 rounded-full opacity-0 transition-opacity duration-200 group-hover:opacity-70" />
			<div className="flex items-start justify-between gap-2">
				{labelNode}
				<div className="flex items-center gap-1">
					{explanation ? <MetricExplanationControl {...explanation} /> : null}
					{icon ? (
						<span className="text-muted-foreground group-hover:text-primary transition-colors duration-200">
							{icon}
						</span>
					) : null}
				</div>
			</div>
			{loading ? (
				<Skeleton className="mt-3 h-7 w-24" />
			) : (
				<div
					data-slot="metric-value"
					className={cn('num mt-2 text-2xl font-semibold tabular-nums tracking-normal', toneClass)}
				>
					{value}
				</div>
			)}
			<div className="text-muted-foreground mt-1 flex items-center gap-1.5 text-xs">
				{delta !== undefined && delta !== null && !Number.isNaN(delta) ? (
					<span
						className={cn(
							'inline-flex items-center gap-0.5 font-medium',
							delta >= 0 ? 'text-positive' : 'text-negative'
						)}
					>
						{delta >= 0 ? <TrendingUp className="size-3" /> : <TrendingDown className="size-3" />}
						{(delta * 100).toFixed(2)}%
					</span>
				) : null}
				{hint ? <span className="truncate">{hint}</span> : null}
			</div>
		</Card>
	);
}

function MetricExplanationControl({
	portfolioId,
	metric
}: {
	portfolioId: string;
	metric: string;
}) {
	const [open, setOpen] = useState(false);
	const explanation = useMetricExplanation(portfolioId, metric, open);
	return (
		<Popover open={open} onOpenChange={setOpen}>
			<PopoverTrigger asChild>
				<Button variant="ghost" size="icon" className="size-6" aria-label="Explain this metric">
					<HelpCircle className="size-3.5" />
				</Button>
			</PopoverTrigger>
			<PopoverContent align="end" className="w-[min(22rem,calc(100vw-2rem))] space-y-3">
				{explanation.isLoading ? (
					<InlineSpinner label="Loading explanation" />
				) : explanation.data ? (
					<>
						<div>
							<p className="font-medium">{explanation.data.title}</p>
							<p className="text-muted-foreground mt-1 text-xs leading-5">
								{explanation.data.definition}
							</p>
						</div>
						<div className="bg-surface-strong/50 rounded-md border p-2.5 text-xs">
							<p className="font-medium">Current value: {explanation.data.value}</p>
							<p className="text-muted-foreground mt-1 leading-5">
								{explanation.data.interpretation}
							</p>
						</div>
						<p className="text-muted-foreground text-xs leading-5">
							{explanation.data.why_it_matters}
						</p>
						<div className="text-muted-foreground flex items-center justify-between gap-2 text-xs">
							<span>{explanation.data.source.replaceAll('_', ' ')}</span>
							{explanation.data.data_as_of ? (
								<span>As of {explanation.data.data_as_of}</span>
							) : null}
						</div>
						<Button asChild size="sm" variant="outline" className="w-full">
							<Link href={`/ai-copilot?prompt=${encodeURIComponent(explanation.data.ask_prompt)}`}>
								Ask Copilot about this
							</Link>
						</Button>
					</>
				) : (
					<p className="text-negative text-xs">The explanation is temporarily unavailable.</p>
				)}
			</PopoverContent>
		</Popover>
	);
}

export function InlineSpinner({ label }: { label?: string }) {
	return (
		<span className="text-muted-foreground inline-flex items-center gap-2 text-sm">
			<Loader2 className="size-3.5 animate-spin" />
			{label ?? 'Loading'}
		</span>
	);
}
