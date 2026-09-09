'use client';

import { Activity, HelpCircle, TrendingDown, TrendingUp } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import type { ReactNode } from 'react';
import { toast } from 'sonner';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { formatNumber } from '@/lib/format';
import { useLivePrices } from '@/lib/queries';
import { cn } from '@/lib/utils';

const statChips = ['4 Regime States', 'Real-time VaR & CVaR', 'AI Regime Explanations'];
const tapeTickers = [
	'^NSEI',
	'^BSESN',
	'^NSEBANK',
	'RELIANCE.NS',
	'HDFCBANK.NS',
	'BHARTIARTL.NS',
	'HINDUNILVR.NS',
	'INFY.NS',
	'TCS.NS',
	'ICICIBANK.NS',
	'MARUTI.NS',
	'ITC.NS'
];
const fallbackTape = [
	{ ticker: 'NIFTY', price: 0 },
	{ ticker: 'SENSEX', price: 0 },
	{ ticker: 'BANKNIFTY', price: 0 },
	{ ticker: 'HDFCBANK', price: 0 },
	{ ticker: 'RELIANCE', price: 0 },
	{ ticker: 'INFY', price: 0 },
	{ ticker: 'TCS', price: 0 },
	{ ticker: 'ITC', price: 0 }
];

const tapeDeltas = [0.41, -0.22, 0.18, -0.36, 0.27, 0.09, -0.14, 0.31, -0.08, 0.23, -0.19, 0.12];

type TapeRow = {
	ticker: string;
	price: number;
	delta: number;
};

function BrandHeader() {
	return (
		<div className="flex items-center gap-3">
			<Image
				src="/brand/latent-tile-dark.png"
				alt="Latent logo"
				width={44}
				height={44}
				priority
				className="size-11 rounded-xl object-cover"
			/>
			<div>
				<p className="text-base font-medium text-white">Latent</p>
				<p className="text-muted-foreground text-sm">Portfolio Regime Intelligence</p>
			</div>
		</div>
	);
}

function MarketTape() {
	const { data } = useLivePrices(tapeTickers, true);
	const liveRows: TapeRow[] = data?.length
		? data.map((item, index) => ({
				ticker: item.ticker
					.replace('.NS', '')
					.replace('^NSEI', 'NIFTY')
					.replace('^BSESN', 'SENSEX')
					.replace('^NSEBANK', 'BANKNIFTY'),
				price: item.price,
				delta: tapeDeltas[index % tapeDeltas.length] ?? 0
			}))
		: fallbackTape.map((item, index) => ({
				...item,
				delta: tapeDeltas[index % tapeDeltas.length] ?? 0
			}));
	const rows = [...liveRows, ...liveRows];

	return (
		<div className="border-b border-white/10 bg-[#080B12] py-2">
			<div className="auth-market-tape flex w-max items-center gap-7 px-4">
				{rows.map((item, index) => (
					<div
						key={`${item.ticker}-${index}`}
						className="flex items-center gap-2 text-xs sm:text-sm"
					>
						<span className="font-medium text-white/90">{item.ticker}</span>
						<span className="text-muted-foreground">
							{item.price ? formatNumber(item.price, 2) : 'syncing'}
						</span>
						<span
							className={cn(
								'inline-flex items-center gap-1 tabular-nums',
								item.delta >= 0 ? 'text-emerald-400' : 'text-red-400'
							)}
						>
							{item.delta >= 0 ? (
								<TrendingUp className="size-3" />
							) : (
								<TrendingDown className="size-3" />
							)}
							{Math.abs(item.delta).toFixed(2)}%
						</span>
					</div>
				))}
			</div>
		</div>
	);
}

function DividerWithText() {
	return (
		<div className="relative flex items-center py-1">
			<Separator className="bg-white/10" />
			<span className="text-muted-foreground absolute left-1/2 -translate-x-1/2 bg-[#10141F] px-3 text-xs">
				or
			</span>
		</div>
	);
}

export function AuthShell({
	title,
	subtitle,
	children,
	footer,
	className
}: {
	title: string;
	subtitle: string;
	children: ReactNode;
	footer: ReactNode;
	className?: string;
}) {
	const router = useRouter();
	const { continueAsGuest } = useAuth();
	const [guestLoading, setGuestLoading] = useState(false);

	const startGuest = async () => {
		setGuestLoading(true);
		try {
			await continueAsGuest();
			router.replace('/dashboard');
		} catch (error) {
			toast.error(errorMessage(error));
		} finally {
			setGuestLoading(false);
		}
	};

	return (
		<main className="dark min-h-screen overflow-x-hidden bg-[#0A0D14] text-white">
			<MarketTape />
			<div className="mx-auto grid min-h-[calc(100vh-2.5rem)] w-full max-w-7xl grid-cols-1 items-center gap-8 px-5 py-7 md:px-8 lg:grid-cols-5 lg:gap-12 lg:px-12">
				<section className="flex min-w-0 flex-col justify-center lg:col-span-3">
					<div className="mb-8 flex items-center justify-between gap-4 lg:mb-12">
						<BrandHeader />
					</div>

					<div className="min-w-0">
						<h1 className="max-w-2xl text-4xl font-light leading-tight text-white sm:text-5xl xl:text-6xl">
							See the hidden state behind your portfolio.
						</h1>
						<p className="text-muted-foreground mt-5 max-w-2xl text-base font-normal leading-7 md:text-lg">
							Latent uses Hidden Markov Models to detect market regimes in real time and shows you
							what your risk actually looks like, not just on average, but right now.
						</p>
					</div>
				</section>

				<section
					className={cn('flex min-w-0 items-center justify-center lg:col-span-2', className)}
				>
					<Card className="w-full max-w-[28rem] rounded-2xl border border-white/[0.08] bg-white/[0.03] p-0 text-white shadow-none backdrop-blur-2xl transition-colors duration-200 ease-in-out hover:border-white/15">
						<CardHeader className="space-y-3 p-8 pb-5">
							<Badge className="hover:bg-emerald-400/12 w-fit border border-emerald-400/15 bg-emerald-400/10 px-3 py-1.5 text-sm font-normal text-emerald-300 shadow-none transition-colors duration-200 ease-in-out">
								<Activity className="mr-2 size-3.5" />
								Portfolio intelligence access
							</Badge>
							<div className="space-y-2">
								<CardTitle className="text-xl font-medium text-white">{title}</CardTitle>
								<CardDescription className="text-muted-foreground text-sm font-normal leading-6">
									{subtitle}
								</CardDescription>
							</div>
						</CardHeader>
						<CardContent className="space-y-4 p-8 pt-0">
							<div className="space-y-2">
								<div className="flex items-center gap-2">
									<Button
										type="button"
										variant="outline"
										className="h-10 flex-1 border-white/10 bg-transparent text-white shadow-none transition-colors duration-200 ease-in-out hover:border-[#0EA5E9]/60 hover:bg-white/[0.04] hover:text-white"
										disabled={guestLoading}
										onClick={() => void startGuest()}
									>
										{guestLoading ? 'Starting guest session...' : 'Continue as Guest'}
									</Button>
									<Tooltip>
										<TooltipTrigger asChild>
											<Button
												type="button"
												variant="ghost"
												size="icon"
												aria-label="Guest and account difference"
												className="text-muted-foreground size-10 border border-white/10 shadow-none transition-colors duration-200 ease-in-out hover:border-[#0EA5E9]/40 hover:bg-white/[0.04] hover:text-white"
											>
												<HelpCircle className="size-4" />
											</Button>
										</TooltipTrigger>
										<TooltipContent className="max-w-72 text-sm leading-5">
											Guest mode is temporary for this browser tab. An account saves portfolios,
											trades, history, and analytics so you can return later.
										</TooltipContent>
									</Tooltip>
								</div>
								<p className="text-muted-foreground text-xs leading-5">
									No account needed. Your session stays in this tab only.
								</p>
							</div>

							<DividerWithText />

							{children}

							<div className="text-muted-foreground text-center text-sm">{footer}</div>
						</CardContent>
					</Card>
				</section>
			</div>
		</main>
	);
}

export function AuthFooterLink({
	label,
	href,
	children
}: {
	label: string;
	href: string;
	children: ReactNode;
}) {
	return (
		<span className="inline-flex flex-wrap items-center justify-center gap-1">
			{label}
			<Button
				asChild
				variant="link"
				size="sm"
				className="h-auto px-0 py-0 text-sm font-medium text-[#22D3EE] shadow-none transition-colors duration-200 ease-in-out hover:text-[#67E8F9]"
			>
				<Link href={href}>{children}</Link>
			</Button>
		</span>
	);
}
