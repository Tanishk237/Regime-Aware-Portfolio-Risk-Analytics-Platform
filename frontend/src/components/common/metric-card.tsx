import { Loader2, TrendingDown, TrendingUp } from 'lucide-react';
import type { ReactNode } from 'react';

import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

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
	className
}: MetricCardProps) {
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
		<Card className={cn('panel-surface border-border/80 gap-0 p-4', className)}>
			<div className="flex items-start justify-between gap-2">
				{labelNode}
				{icon ? <span className="text-muted-foreground">{icon}</span> : null}
			</div>
			{loading ? (
				<Skeleton className="mt-3 h-7 w-24" />
			) : (
				<div className={cn('num mt-2 text-xl font-semibold tabular-nums', toneClass)}>{value}</div>
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

export function InlineSpinner({ label }: { label?: string }) {
	return (
		<span className="text-muted-foreground inline-flex items-center gap-2 text-sm">
			<Loader2 className="size-3.5 animate-spin" />
			{label ?? 'Loading'}
		</span>
	);
}
