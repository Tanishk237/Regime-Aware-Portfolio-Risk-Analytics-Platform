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
		<Card
			role="region"
			aria-label={title}
			className={cn('panel-surface border-border/70 gap-3 overflow-hidden py-4', className)}
		>
			<CardHeader className="gap-1 px-4 sm:px-5">
				<div className="flex flex-wrap items-start justify-between gap-2">
					<div className="min-w-0">
						<CardTitle className="text-sm font-medium">{title}</CardTitle>
						{description ? (
							<CardDescription className="mt-1 max-w-prose text-xs leading-5">
								{description}
							</CardDescription>
						) : null}
					</div>
					{action}
				</div>
			</CardHeader>
			<CardContent className={cn('px-2 pb-0 sm:px-5', bodyClassName)}>{children}</CardContent>
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
		<section className={cn('min-w-0 border-b border-border/70 py-4', className)}>
			<header className="mb-4">
				<div className="flex flex-wrap items-start justify-between gap-2">
					<div>
						<h2 className="text-base font-medium">{title}</h2>
						{description ? (
							<p className="text-muted-foreground mt-1 text-sm leading-6">{description}</p>
						) : null}
					</div>
					{action}
				</div>
			</header>
			{children}
		</section>
	);
}
