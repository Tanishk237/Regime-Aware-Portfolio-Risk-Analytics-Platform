import type { ReactNode } from 'react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export function ChartCard({
	title,
	description,
	action,
	children,
	className,
	bodyClassName
}: {
	title: string;
	description?: string;
	action?: ReactNode;
	children: ReactNode;
	className?: string;
	bodyClassName?: string;
}) {
	return (
		<Card className={cn('panel-surface border-border/80 gap-3 py-4', className)}>
			<CardHeader className="gap-1 px-4">
				<div className="flex flex-wrap items-start justify-between gap-2">
					<div>
						<CardTitle className="text-sm font-semibold">{title}</CardTitle>
						{description ? (
							<CardDescription className="text-xs">{description}</CardDescription>
						) : null}
					</div>
					{action}
				</div>
			</CardHeader>
			<CardContent className={cn('px-2 pb-0 sm:px-4', bodyClassName)}>{children}</CardContent>
		</Card>
	);
}

export function SectionCard({
	title,
	description,
	action,
	children,
	className
}: {
	title: string;
	description?: string;
	action?: ReactNode;
	children: ReactNode;
	className?: string;
}) {
	return (
		<Card className={cn('panel-surface border-border/80 gap-3 py-4', className)}>
			<CardHeader className="gap-1 px-4">
				<div className="flex flex-wrap items-start justify-between gap-2">
					<div>
						<CardTitle className="text-sm font-semibold">{title}</CardTitle>
						{description ? (
							<CardDescription className="text-xs">{description}</CardDescription>
						) : null}
					</div>
					{action}
				</div>
			</CardHeader>
			<CardContent className="px-4">{children}</CardContent>
		</Card>
	);
}
