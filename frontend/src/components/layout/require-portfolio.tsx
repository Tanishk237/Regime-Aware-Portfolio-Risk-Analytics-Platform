'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Briefcase, Plus, ScrollText, Upload } from 'lucide-react';
import { toast } from 'sonner';

import { EmptyState } from '@/components/common/states';
import { Button } from '@/components/ui/button';
import { useSelectedPortfolio } from '@/lib/portfolio-context';
import { useDemoPortfolio } from '@/lib/queries';

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
				title="Start with a portfolio"
				description={`Create one manually or upload your trades CSV to unlock ${label}.`}
				action={
					<div className="flex flex-col gap-2 sm:flex-row">
						<Button asChild size="sm">
							<Link href="/upload">
								<Upload className="size-4" /> Upload CSV
							</Link>
						</Button>
						<Button asChild size="sm" variant="outline">
							<Link href="/portfolios">
								<Plus className="size-4" /> Create Portfolio
							</Link>
						</Button>
						<DemoPortfolioButton />
					</div>
				}
			/>
		);
	}

	if (!selectedId) return null;
	return <>{children(selectedId)}</>;
}

function DemoPortfolioButton() {
	const router = useRouter();
	const { select } = useSelectedPortfolio();
	const demoPortfolio = useDemoPortfolio();

	const createDemo = async () => {
		try {
			const result = await demoPortfolio.create.mutateAsync();
			select(result.portfolio.id);
			toast.success('Demo portfolio is ready');
			router.push('/dashboard');
		} catch {
			toast.error('Could not prepare the demo portfolio.');
		}
	};

	return (
		<Button
			size="sm"
			variant="ghost"
			onClick={() => void createDemo()}
			disabled={demoPortfolio.create.isPending}
		>
			{demoPortfolio.create.isPending ? 'Preparing demo...' : 'Try Demo'}
		</Button>
	);
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
