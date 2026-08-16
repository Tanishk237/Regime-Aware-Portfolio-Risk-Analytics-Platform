'use client';

import Link from 'next/link';
import { Briefcase, Plus, ScrollText } from 'lucide-react';

import { EmptyState } from '@/components/common/states';
import { Button } from '@/components/ui/button';
import { useSelectedPortfolio } from '@/lib/portfolio-context';

/** Renders children only when a portfolio is selected, otherwise a CTA empty state. */
export function RequirePortfolio({
	children,
	label = 'analytics'
}: {
	children: (portfolioId: string) => React.ReactNode;
	label?: string;
}) {
	const { portfolios, isLoading, selectedId } = useSelectedPortfolio();

	if (isLoading) return null;

	if (portfolios.length === 0) {
		return (
			<EmptyState
				icon={<Briefcase className="size-5" />}
				title="Create a portfolio to begin"
				description={`Create your first portfolio to unlock ${label}.`}
				action={
					<Button asChild size="sm">
						<Link href="/portfolios">
							<Plus className="size-4" /> Create Portfolio
						</Link>
					</Button>
				}
			/>
		);
	}

	if (!selectedId) return null;
	return <>{children(selectedId)}</>;
}

export function NoTradesState() {
	return (
		<EmptyState
			icon={<ScrollText className="size-5" />}
			title="Add trades or upload CSV to unlock analytics"
			description="Positions, P&L, risk and regime analytics are all derived from your trade history."
			action={
				<div className="flex flex-wrap justify-center gap-2">
					<Button asChild size="sm">
						<Link href="/trades">Add a trade</Link>
					</Button>
					<Button asChild size="sm" variant="outline">
						<Link href="/upload">Upload CSV</Link>
					</Button>
				</div>
			}
		/>
	);
}
