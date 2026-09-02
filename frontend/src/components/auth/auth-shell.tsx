'use client';

import { motion } from 'motion/react';
import {
	Activity,
	BadgeCheck,
	Bot,
	ChartNoAxesCombined,
	LineChart,
	LockKeyhole,
	ShieldCheck
} from 'lucide-react';
import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

const metrics = [
	{ label: 'Risk score', value: '63/100', delta: 'Aggressive' },
	{ label: 'Regime', value: 'Bull', delta: '90% confidence' },
	{ label: 'Drawdown', value: '-7.26%', delta: '1Y window' }
];

const chartPoints = '4,112 54,98 104,106 154,76 204,84 254,50 304,62 354,34 404,46';

function MetricRow({ label, value, delta }: (typeof metrics)[number]) {
	return (
		<div className="flex items-center justify-between gap-4 border-b border-white/10 py-3 last:border-0">
			<div>
				<p className="text-muted-foreground text-xs">{label}</p>
				<p className="num text-foreground mt-1 text-lg font-semibold">{value}</p>
			</div>
			<p className="text-muted-foreground text-right text-xs">{delta}</p>
		</div>
	);
}

function MarketVisual() {
	return (
		<div className="relative mt-10 grid gap-4 xl:grid-cols-[minmax(0,1fr)_18rem]">
			<div className="shadow-elegant relative min-h-[25rem] overflow-hidden rounded-2xl border border-white/10 bg-white/[0.035] p-5">
				<div className="auth-chart-grid absolute inset-0" />
				<div className="relative flex items-center justify-between gap-4">
					<div>
						<p className="text-muted-foreground text-xs uppercase tracking-[0.18em]">
							Portfolio monitor
						</p>
						<p className="mt-1 text-sm font-medium">Sample Indian equity basket</p>
					</div>
					<div className="border-positive/25 bg-positive/10 text-positive flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium">
						<span className="bg-positive size-1.5 rounded-full" />
						Live
					</div>
				</div>

				<motion.div
					className="bg-background/55 relative mt-10 rounded-xl border border-white/10 p-5 backdrop-blur-xl"
					initial={{ opacity: 0, y: 18 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.55, delay: 0.1 }}
				>
					<div className="mb-4 flex items-center justify-between">
						<div>
							<p className="text-muted-foreground text-xs">Portfolio value</p>
							<p className="num mt-1 text-2xl font-semibold">₹1.30L</p>
						</div>
						<div className="border-primary/25 bg-primary/10 text-primary rounded-full border px-3 py-1 text-sm font-medium">
							Bull regime
						</div>
					</div>
					<svg className="h-36 w-full overflow-visible" viewBox="0 0 408 130" role="img">
						<title>Portfolio growth line</title>
						<defs>
							<linearGradient id="auth-chart-fill" x1="0" x2="0" y1="0" y2="1">
								<stop offset="0%" stopColor="oklch(0.7 0.15 275 / 0.32)" />
								<stop offset="100%" stopColor="oklch(0.75 0.14 190 / 0.02)" />
							</linearGradient>
						</defs>
						<path d={`M ${chartPoints} L 404,126 L 4,126 Z`} fill="url(#auth-chart-fill)" />
						<motion.polyline
							points={chartPoints}
							fill="none"
							stroke="oklch(0.72 0.14 196)"
							strokeWidth="3.5"
							strokeLinecap="round"
							strokeLinejoin="round"
							initial={{ pathLength: 0 }}
							animate={{ pathLength: 1 }}
							transition={{ duration: 1.5, ease: 'easeInOut' }}
						/>
					</svg>
				</motion.div>

				<div className="relative mt-4 grid grid-cols-3 gap-3">
					{[
						{ label: 'VaR', value: '3.2%' },
						{ label: 'Sharpe', value: '0.84' },
						{ label: 'Trades', value: '10' }
					].map((item) => (
						<div
							key={item.label}
							className="bg-background/45 rounded-lg border border-white/10 px-3 py-3"
						>
							<p className="text-muted-foreground text-xs">{item.label}</p>
							<p className="num mt-1 font-semibold">{item.value}</p>
						</div>
					))}
				</div>
			</div>

			<motion.div
				className="shadow-elegant relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.035] p-5"
				initial={{ opacity: 0, y: 18 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ duration: 0.55, delay: 0.2 }}
			>
				<div className="auth-orb mx-auto mb-6 mt-2 flex size-28 items-center justify-center rounded-full">
					<LineChart className="text-primary size-9" />
				</div>
				<div>
					{metrics.map((metric) => (
						<MetricRow key={metric.label} {...metric} />
					))}
				</div>
				<div className="border-warning/20 bg-warning/10 mt-5 rounded-lg border p-3">
					<p className="text-warning text-xs font-medium">Recommendation</p>
					<p className="text-muted-foreground mt-1 text-xs leading-5">
						Review concentration before adding fresh capital.
					</p>
				</div>
			</motion.div>
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
	return (
		<main className="auth-page bg-background text-foreground dark min-h-screen overflow-hidden">
			<div className="auth-visual-glow absolute inset-0" />
			<div className="relative mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-10">
				<header className="flex items-center justify-between">
					<div className="flex items-center gap-3">
						<div className="bg-gradient-brand text-primary-foreground shadow-elegant flex size-11 items-center justify-center rounded-xl text-sm font-bold">
							R
						</div>
						<div>
							<p className="font-semibold">Regime Aware</p>
							<p className="text-muted-foreground text-sm">Portfolio Risk Analytics</p>
						</div>
					</div>
					<div className="text-muted-foreground hidden items-center gap-2 rounded-full border border-white/10 bg-white/[0.035] px-3 py-1.5 text-sm sm:flex">
						<LockKeyhole className="text-primary size-4" />
						Secure portfolio workspace
					</div>
				</header>

				<div className="grid flex-1 items-center gap-10 py-10 lg:grid-cols-[minmax(0,1.3fr)_minmax(22rem,0.7fr)]">
					<section className="hidden lg:block">
						<div className="max-w-4xl">
							<motion.h1
								className="max-w-4xl text-5xl font-semibold leading-tight tracking-normal xl:text-6xl"
								initial={{ opacity: 0, y: 18 }}
								animate={{ opacity: 1, y: 0 }}
								transition={{ duration: 0.55 }}
							>
								Know when your portfolio risk is changing.
							</motion.h1>
							<motion.p
								className="text-muted-foreground mt-5 max-w-2xl text-lg leading-8"
								initial={{ opacity: 0, y: 14 }}
								animate={{ opacity: 1, y: 0 }}
								transition={{ duration: 0.55, delay: 0.12 }}
							>
								A connected workspace for trades, market data, HMM regimes, risk analytics, stress
								tests, recommendations, and AI summaries.
							</motion.p>
							<MarketVisual />
							<div className="mt-5 grid grid-cols-3 gap-3">
								{[
									{ icon: Activity, label: 'Live risk' },
									{ icon: ShieldCheck, label: 'User scoped' },
									{ icon: Bot, label: 'AI reports' }
								].map((item) => (
									<div
										key={item.label}
										className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/[0.035] px-4 py-3"
									>
										<item.icon className="text-primary size-5" />
										<p className="text-sm font-medium">{item.label}</p>
									</div>
								))}
							</div>
						</div>
					</section>

					<section className={cn('mx-auto w-full max-w-md lg:ml-auto', className)}>
						<div className="mb-8 lg:hidden">
							<h1 className="text-3xl font-semibold">Regime Aware Portfolio Risk Analytics</h1>
							<p className="text-muted-foreground mt-2 text-base">
								Portfolio risk, regimes, and decision intelligence.
							</p>
							<div className="mt-5 grid grid-cols-3 gap-2">
								{[
									{ label: 'VaR', value: '3.2%' },
									{ label: 'Regime', value: 'Bull' },
									{ label: 'Health', value: '82' }
								].map((item) => (
									<div
										key={item.label}
										className="rounded-lg border border-white/10 bg-white/[0.035] px-3 py-2"
									>
										<p className="text-muted-foreground text-xs">{item.label}</p>
										<p className="num mt-1 text-sm font-semibold">{item.value}</p>
									</div>
								))}
							</div>
						</div>
						<motion.div
							className="bg-card/90 shadow-elegant rounded-2xl border border-white/10 p-6 backdrop-blur-xl sm:p-8"
							initial={{ opacity: 0, y: 18 }}
							animate={{ opacity: 1, y: 0 }}
							transition={{ duration: 0.45, delay: 0.08 }}
						>
							<div className="mb-6">
								<div className="text-primary mb-4 flex items-center gap-2">
									<BadgeCheck className="size-4" />
									<span className="text-sm font-medium">Production analytics access</span>
								</div>
								<h2 className="text-2xl font-semibold">{title}</h2>
								<p className="text-muted-foreground mt-2 text-sm leading-6">{subtitle}</p>
							</div>
							{children}
							<div className="text-muted-foreground mt-5 text-center text-sm">{footer}</div>
							<div className="text-muted-foreground mt-6 flex items-center justify-center gap-2 border-t border-white/10 pt-5 text-xs">
								<ChartNoAxesCombined className="text-primary size-4" />
								Risk, regimes, and AI reports stay linked to your account.
							</div>
						</motion.div>
					</section>
				</div>
			</div>
		</main>
	);
}
