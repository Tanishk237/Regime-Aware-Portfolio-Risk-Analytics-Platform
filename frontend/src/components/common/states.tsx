import { AlertTriangle, Info, Inbox, RefreshCw } from 'lucide-react';
import type { ReactNode } from 'react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { errorMessage } from '@/lib/api';
import { cn } from '@/lib/utils';

export function EmptyState({
	title,
	description,
	action,
	icon,
	className
}: {
	title: string;
	description?: string;
	action?: ReactNode;
	icon?: ReactNode;
	className?: string;
}) {
	return (
		<div
			className={cn(
				'bg-surface/70 flex flex-col items-center justify-center rounded-xl border border-dashed px-6 py-12 text-center shadow-inner',
				className
			)}
		>
			<div className="bg-surface-strong text-muted-foreground mb-3 flex size-11 items-center justify-center rounded-full border">
				{icon ?? <Inbox className="size-5" />}
			</div>
			<p className="text-sm font-semibold">{title}</p>
			{description ? (
				<p className="text-muted-foreground mt-1 max-w-md text-sm">{description}</p>
			) : null}
			{action ? <div className="mt-4">{action}</div> : null}
		</div>
	);
}

export function ErrorState({
	error,
	onRetry,
	className
}: {
	error: unknown;
	onRetry?: () => void;
	className?: string;
}) {
	return (
		<div
			className={cn(
				'border-negative/30 bg-negative-muted/60 shadow-soft flex flex-col items-start gap-3 rounded-xl border p-4 sm:flex-row sm:items-center sm:justify-between',
				className
			)}
		>
			<div className="flex items-start gap-2.5">
				<AlertTriangle className="text-negative mt-0.5 size-4 shrink-0" />
				<div>
					<p className="text-negative text-sm font-semibold">Request failed</p>
					<p className="text-foreground/80 text-sm">{errorMessage(error)}</p>
				</div>
			</div>
			{onRetry ? (
				<Button variant="outline" size="sm" onClick={onRetry}>
					<RefreshCw className="size-3.5" /> Retry
				</Button>
			) : null}
		</div>
	);
}

export function WarningState({
	title,
	description,
	className
}: {
	title: string;
	description?: string;
	className?: string;
}) {
	return (
		<div
			className={cn(
				'border-warning/30 bg-warning-muted/60 shadow-soft flex items-start gap-2.5 rounded-xl border p-4',
				className
			)}
		>
			<Info className="text-warning mt-0.5 size-4 shrink-0" />
			<div>
				<p className="text-sm font-semibold">{title}</p>
				{description ? <p className="text-muted-foreground mt-1 text-sm">{description}</p> : null}
			</div>
		</div>
	);
}

export function LoadingSkeleton({ rows = 4, className }: { rows?: number; className?: string }) {
	return (
		<div className={cn('space-y-2', className)}>
			{Array.from({ length: rows }).map((_, index) => (
				<Skeleton key={index} className="h-10 w-full" />
			))}
		</div>
	);
}

export function MetricGridSkeleton({ count = 4 }: { count?: number }) {
	return (
		<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
			{Array.from({ length: count }).map((_, index) => (
				<Card key={index} className="gap-0 p-4">
					<Skeleton className="h-3 w-20" />
					<Skeleton className="mt-3 h-6 w-28" />
					<Skeleton className="mt-2 h-3 w-16" />
				</Card>
			))}
		</div>
	);
}
