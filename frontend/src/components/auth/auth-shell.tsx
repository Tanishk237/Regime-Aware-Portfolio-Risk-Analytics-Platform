'use client';

import { Activity, HelpCircle } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import type { ReactNode } from 'react';
import { toast } from 'sonner';

import { LatentBrand } from '@/components/brand/latent-brand';
import { ThemeToggle } from '@/components/theme/theme-toggle';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { formatNumber } from '@/lib/format';
import { useDemoPortfolio, useLivePrices } from '@/lib/queries';
import { cn } from '@/lib/utils';

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

type TapeRow = {
	ticker: string;
	price: number;
};

function BrandHeader() {
	return (
		<div className="flex w-full items-center justify-between gap-4">
			<LatentBrand size="md" />
			<ThemeToggle className="border-border/70 bg-card/60 border" />
		</div>
	);
}

function MarketTape() {
	const { data } = useLivePrices(tapeTickers, true);
	const liveRows: TapeRow[] = data?.length
		? data.map((item) => ({
				ticker: item.ticker
					.replace('.NS', '')
					.replace('^NSEI', 'NIFTY')
					.replace('^BSESN', 'SENSEX')
					.replace('^NSEBANK', 'BANKNIFTY'),
				price: item.price
			}))
		: fallbackTape;
	const rows = [...liveRows, ...liveRows];

	return (
		<div className="border-border/70 bg-card/70 group relative overflow-hidden border-b py-2 backdrop-blur-xl">
			<div className="from-card pointer-events-none absolute inset-y-0 left-0 z-10 w-12 bg-gradient-to-r to-transparent" />
			<div className="from-card pointer-events-none absolute inset-y-0 right-0 z-10 w-12 bg-gradient-to-l to-transparent" />
			<div className="auth-market-tape flex w-max items-center gap-7 px-4">
				{rows.map((item, index) => (
					<div
						key={`${item.ticker}-${index}`}
						className="flex items-center gap-2 text-xs sm:text-sm"
					>
						<span className="bg-primary/80 size-1.5 rounded-full" aria-hidden />
						<span className="text-foreground/90 font-medium">{item.ticker}</span>
						<span className="text-muted-foreground">
							{item.price ? formatNumber(item.price, 2) : 'syncing'}
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
			<span className="bg-card text-muted-foreground absolute left-1/2 -translate-x-1/2 px-3 text-xs">
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
	const { continueAsGuest, hydrated } = useAuth();
	const demoPortfolio = useDemoPortfolio();
	const [guestLoading, setGuestLoading] = useState(false);

	const startGuest = async (withDemo = false) => {
		setGuestLoading(true);
		try {
			await continueAsGuest();
			if (withDemo) {
				await demoPortfolio.create.mutateAsync();
				router.replace('/dashboard');
				return;
			}
			router.replace('/upload');
		} catch (error) {
			toast.error(errorMessage(error));
		} finally {
			setGuestLoading(false);
		}
	};

	return (
		<main className="bg-background text-foreground flex min-h-screen flex-col overflow-x-hidden">
			<MarketTape />
			<div className="mx-auto grid w-full max-w-7xl flex-1 grid-cols-1 items-start gap-4 px-5 py-4 sm:gap-6 sm:py-7 md:px-8 lg:grid-cols-5 lg:items-center lg:gap-10 lg:px-12">
				<section className="auth-hero-enter flex min-w-0 flex-col justify-center lg:col-span-3">
					<div className="mb-4 flex items-center justify-between gap-4 sm:mb-8 lg:mb-12">
						<BrandHeader />
					</div>

					<div className="min-w-0">
						<h1 className="text-foreground max-w-2xl text-3xl font-light leading-tight sm:text-5xl xl:text-6xl">
							See the hidden state behind your portfolio.
						</h1>
						<p className="text-muted-foreground mt-3 hidden max-w-2xl text-sm font-normal leading-6 sm:mt-5 sm:block sm:text-base sm:leading-7 md:text-lg">
							Latent uses Hidden Markov Models to detect market regimes in real time and shows you
							what your risk actually looks like, not just on average, but right now.
						</p>
						<div className="mt-9 hidden max-w-2xl sm:block" aria-hidden="true">
							<div className="text-muted-foreground mb-3 flex items-center justify-between text-xs">
								<span>Latent market-state field</span>
								<span className="inline-flex items-center gap-2">
									<span className="bg-positive auth-live-dot size-1.5 rounded-full" />
									Signal active
								</span>
							</div>
							<svg viewBox="0 0 680 150" className="h-36 w-full overflow-visible">
								<path d="M0 79 H680" fill="none" stroke="var(--border)" strokeDasharray="4 10" />
								<path d="M428 6 V142" fill="none" stroke="var(--border)" strokeDasharray="3 8" />
								<path
									className="auth-signal-contour auth-signal-contour-one"
									d="M-18 112 C75 107 92 18 184 29 S298 139 389 101 S488 8 562 37 S628 119 704 72"
									fill="none"
									stroke="var(--chart-1)"
									strokeWidth="1"
								/>
								<path
									className="auth-signal-contour auth-signal-contour-two"
									d="M-14 125 C70 116 103 39 185 45 S293 130 382 111 S485 24 560 52 S627 125 700 84"
									fill="none"
									stroke="var(--chart-2)"
									strokeWidth="1"
								/>
								<path
									className="auth-signal-contour auth-signal-contour-three"
									d="M-10 137 C78 127 114 60 192 61 S292 126 376 120 S478 42 553 68 S628 132 696 98"
									fill="none"
									stroke="var(--muted-foreground)"
									strokeWidth="1"
								/>
								<path
									className="auth-signal-line"
									d="M-18 112 C75 107 92 18 184 29 S298 139 389 101 S488 8 562 37 S628 119 704 72"
									fill="none"
									stroke="var(--chart-2)"
									strokeWidth="2.75"
									strokeLinecap="round"
								/>
								<circle
									className="auth-signal-pulse"
									cx="428"
									cy="58"
									r="5"
									fill="var(--chart-2)"
								/>
								<circle
									cx="184"
									cy="29"
									r="3"
									fill="var(--background)"
									stroke="var(--chart-1)"
									strokeWidth="2"
								/>
								<circle
									cx="562"
									cy="37"
									r="3"
									fill="var(--background)"
									stroke="var(--chart-2)"
									strokeWidth="2"
								/>
							</svg>
						</div>
					</div>
				</section>

				<section
					className={cn(
						'auth-card-enter flex min-w-0 items-center justify-center lg:col-span-2 lg:border-l lg:pl-10',
						className
					)}
				>
					<Card className="border-border/80 bg-card/82 text-card-foreground hover:border-primary/30 w-full max-w-[28rem] rounded-xl p-0 shadow-none backdrop-blur-2xl transition-colors duration-200 ease-in-out">
						<CardHeader className="space-y-2.5 p-5 pb-4 sm:space-y-3 sm:p-8 sm:pb-5">
							<Badge className="bg-positive-muted text-positive border-positive/20 hover:bg-positive-muted w-fit border px-3 py-1.5 text-sm font-normal shadow-none transition-colors duration-200 ease-in-out">
								<Activity className="mr-2 size-3.5" />
								Portfolio intelligence access
							</Badge>
							<div className="space-y-2">
								<CardTitle className="text-foreground text-xl font-medium">{title}</CardTitle>
								<CardDescription className="text-muted-foreground text-sm font-normal leading-6">
									{subtitle}
								</CardDescription>
							</div>
						</CardHeader>
						<CardContent className="space-y-3.5 p-5 pt-0 sm:space-y-4 sm:p-8 sm:pt-0">
							<div className="space-y-2">
								<div className="flex items-center gap-2">
									<Button
										type="button"
										variant="outline"
										className="border-border/80 text-foreground hover:border-primary/50 hover:bg-accent h-10 flex-1 bg-transparent shadow-none transition-colors duration-200 ease-in-out"
										disabled={!hydrated || guestLoading || demoPortfolio.create.isPending}
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
												className="text-muted-foreground border-border/80 hover:border-primary/40 hover:bg-accent hover:text-foreground size-10 border shadow-none transition-colors duration-200 ease-in-out"
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
									No account needed. Start by uploading a CSV; this session stays in this tab only.
								</p>
								<Button
									type="button"
									variant="ghost"
									className="text-primary hover:text-primary/80 h-8 px-0 text-xs shadow-none hover:bg-transparent"
									disabled={!hydrated || guestLoading || demoPortfolio.create.isPending}
									onClick={() => void startGuest(true)}
								>
									{demoPortfolio.create.isPending
										? 'Preparing demo portfolio...'
										: 'Try a demo portfolio'}
								</Button>
							</div>

							<DividerWithText />

							{children}

							<div className="text-muted-foreground text-center text-sm">{footer}</div>
						</CardContent>
					</Card>
				</section>
			</div>
			<footer className="text-muted-foreground flex flex-wrap items-center justify-center gap-4 px-5 py-4 text-xs">
				<Link className="hover:text-foreground transition-colors" href="/privacy">
					Privacy
				</Link>
				<Link className="hover:text-foreground transition-colors" href="/terms">
					Terms and risk disclosure
				</Link>
			</footer>
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
				className="text-primary hover:text-primary/80 h-auto px-0 py-0 text-sm font-medium shadow-none transition-colors duration-200 ease-in-out"
			>
				<Link href={href}>{children}</Link>
			</Button>
		</span>
	);
}
