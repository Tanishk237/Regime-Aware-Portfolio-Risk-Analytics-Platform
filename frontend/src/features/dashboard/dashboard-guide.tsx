'use client';

import { Activity, ChartNoAxesCombined, HeartPulse, Info } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle
} from '@/components/ui/dialog';

const GUIDE_STORAGE_KEY = 'latent.dashboard-guide.v1';

const GUIDE_ITEMS = [
	{
		icon: ChartNoAxesCombined,
		title: 'What you own',
		description:
			'Holdings value uses the latest available prices. Open-holdings return compares it with the remaining purchase cost. Gains or losses from sold holdings are shown separately.'
	},
	{
		icon: Activity,
		title: 'Current market state',
		description:
			'The market state describes recent behavior, not what will happen next. A model probability is a historical state fit, not forecast accuracy.'
	},
	{
		icon: HeartPulse,
		title: 'Risk context',
		description:
			"Risk metrics model how today's holdings would have behaved over the available history. The risk-review score summarizes that model; it is not a safety rating."
	}
];

export function DashboardGuide({ portfolioId }: { portfolioId: string }) {
	const [open, setOpen] = useState(false);

	useEffect(() => {
		if (window.localStorage.getItem(GUIDE_STORAGE_KEY)) return;
		const timeout = window.setTimeout(() => setOpen(true), 550);
		return () => window.clearTimeout(timeout);
	}, [portfolioId]);

	const updateOpen = (nextOpen: boolean) => {
		setOpen(nextOpen);
		if (!nextOpen) window.localStorage.setItem(GUIDE_STORAGE_KEY, 'seen');
	};

	return (
		<>
			<Button
				size="sm"
				variant="ghost"
				aria-label="How to read this dashboard"
				onClick={() => setOpen(true)}
			>
				<Info className="size-4" />
				<span className="hidden sm:inline">How to read this</span>
			</Button>
			<Dialog open={open} onOpenChange={updateOpen}>
				<DialogContent className="max-w-xl">
					<DialogHeader>
						<DialogTitle>Read your portfolio in three layers</DialogTitle>
						<DialogDescription>
							Start with your holdings, then review risk and the next action worth considering.
						</DialogDescription>
					</DialogHeader>
					<div className="divide-border rounded-lg border">
						{GUIDE_ITEMS.map((item) => (
							<div key={item.title} className="flex gap-3 p-4">
								<div className="bg-primary/10 text-primary flex size-9 shrink-0 items-center justify-center rounded-md">
									<item.icon className="size-4" />
								</div>
								<div>
									<p className="text-sm font-medium">{item.title}</p>
									<p className="text-muted-foreground mt-1 text-sm leading-5">{item.description}</p>
								</div>
							</div>
						))}
					</div>
					<p className="text-muted-foreground text-xs leading-5">
						Hover or focus a dotted metric label for its definition. Figures show an em dash until
						the required market data is available.
					</p>
					<DialogFooter>
						<Button onClick={() => updateOpen(false)}>Explore dashboard</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</>
	);
}
