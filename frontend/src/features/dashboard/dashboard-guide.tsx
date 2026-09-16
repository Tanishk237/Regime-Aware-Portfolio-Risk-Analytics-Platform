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
		title: 'Portfolio outcome',
		description:
			'Current value, invested capital and total return describe where the portfolio stands.'
	},
	{
		icon: Activity,
		title: 'Current market state',
		description:
			'The regime and its confidence show the HMM state inferred from recent market behavior.'
	},
	{
		icon: HeartPulse,
		title: 'Risk context',
		description:
			'Drawdown, volatility, VaR and health explain how much pressure sits behind the return.'
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
			<Button size="sm" variant="ghost" onClick={() => setOpen(true)}>
				<Info className="size-4" />
				<span className="hidden sm:inline">How to read this</span>
			</Button>
			<Dialog open={open} onOpenChange={updateOpen}>
				<DialogContent className="max-w-xl">
					<DialogHeader>
						<DialogTitle>Read your portfolio in three layers</DialogTitle>
						<DialogDescription>
							Latent connects performance with the market state and the risk taken to get there.
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
