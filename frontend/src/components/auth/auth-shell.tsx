'use client';

import { motion } from 'motion/react';
import {
	BadgeCheck,
	BrainCircuit,
	ChartNoAxesCombined,
	LineChart,
	LockKeyhole,
	ShieldCheck
} from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

import { LatentBrand } from '@/components/brand/latent-brand';
import { cn } from '@/lib/utils';

const detailCards = [
	{
		title: 'Portfolio workspace',
		description: 'Create portfolios, upload trades, and keep positions connected to analytics.',
		icon: ShieldCheck
	},
	{
		title: 'Regime intelligence',
		description: 'Read changing market states through model-backed regime views and confidence.',
		icon: BrainCircuit
	},
	{
		title: 'Risk context',
		description: 'Turn returns, drawdowns, volatility, and recommendations into clearer decisions.',
		icon: LineChart
	}
];

function BrandVisual() {
	return (
		<div className="shadow-elegant relative mt-9 aspect-[1.22] w-full max-w-[34rem] overflow-hidden rounded-[2rem] border border-white/10 bg-white/[0.035]">
			<div className="auth-chart-grid absolute inset-0" />
			<div className="auth-brand-plane auth-brand-plane-one" />
			<div className="auth-brand-plane auth-brand-plane-two" />
			<div className="auth-brand-plane auth-brand-plane-three" />

			<motion.div
				className="bg-background/60 shadow-elegant absolute left-1/2 top-1/2 flex size-44 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-[1.75rem] border border-white/10 backdrop-blur-xl"
				initial={{ opacity: 0, scale: 0.94 }}
				animate={{ opacity: 1, scale: 1, y: [0, -10, 0] }}
				transition={{
					opacity: { duration: 0.5 },
					scale: { duration: 0.5 },
					y: { duration: 6, repeat: Infinity, ease: 'easeInOut' }
				}}
			>
				<div className="auth-orb flex size-32 items-center justify-center rounded-full">
					<Image
						src="/brand/latent-mark-white.png"
						alt=""
						width={76}
						height={76}
						className="size-18"
					/>
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
	const pathname = usePathname();
	const isSignup = pathname?.startsWith('/signup');

	return (
		<main className="auth-page bg-background text-foreground dark min-h-screen overflow-hidden">
			<div className="auth-visual-glow absolute inset-0" />
			<div className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-6 sm:px-6 lg:px-10">
				<header className="flex items-center justify-between">
					<LatentBrand variant="dark" />
					<div className="text-muted-foreground hidden items-center gap-2 rounded-full border border-white/10 bg-white/[0.035] px-3 py-1.5 text-sm sm:flex">
						<LockKeyhole className="text-primary size-4" />
						Secure workspace
					</div>
				</header>

				<div className="grid flex-1 items-center gap-10 py-8 lg:grid-cols-[minmax(0,1fr)_27rem] lg:gap-14 xl:gap-20">
					<section className="order-2 lg:order-1">
						<div className="mx-auto max-w-2xl lg:mx-0">
							<div className="text-muted-foreground mb-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.035] px-3 py-1.5 text-sm">
								<span className="bg-primary size-1.5 rounded-full" />
								Built for calmer portfolio decisions
							</div>
							<motion.h1
								className="max-w-2xl text-4xl font-semibold leading-tight tracking-normal sm:text-5xl"
								initial={{ opacity: 0, y: 18 }}
								animate={{ opacity: 1, y: 0 }}
								transition={{ duration: 0.55 }}
							>
								See the hidden state behind your portfolio.
							</motion.h1>
							<motion.p
								className="text-muted-foreground mt-5 max-w-xl text-base leading-7 sm:text-lg"
								initial={{ opacity: 0, y: 14 }}
								animate={{ opacity: 1, y: 0 }}
								transition={{ duration: 0.55, delay: 0.12 }}
							>
								Latent turns market regimes, portfolio risk, and AI explanations into a friendly
								decision workspace.
							</motion.p>

							<div className="mt-8 grid gap-3 sm:grid-cols-3">
								{detailCards.map((item) => {
									const Icon = item.icon;

									return (
										<div
											key={item.title}
											className="rounded-2xl border border-white/10 bg-white/[0.035] p-4 backdrop-blur"
										>
											<Icon className="text-primary mb-3 size-5" />
											<h3 className="text-sm font-semibold">{item.title}</h3>
											<p className="text-muted-foreground mt-2 text-xs leading-5">
												{item.description}
											</p>
										</div>
									);
								})}
							</div>
							<BrandVisual />
						</div>
					</section>

					<section className={cn('order-1 mx-auto w-full max-w-[27rem] lg:order-2', className)}>
						<div className="mb-8 lg:hidden">
							<h1 className="text-3xl font-semibold">Latent</h1>
							<p className="text-muted-foreground mt-2 text-base">
								Portfolio Regime Intelligence for risk-aware investing.
							</p>
						</div>
						<motion.div
							className="bg-card/92 shadow-elegant rounded-[1.75rem] border border-white/10 p-6 backdrop-blur-xl sm:p-8 lg:mt-10"
							initial={{ opacity: 0, y: 18 }}
							animate={{ opacity: 1, y: 0 }}
							transition={{ duration: 0.45, delay: 0.08 }}
						>
							<div className="mb-6">
								<div className="bg-primary/10 text-primary mb-4 inline-flex items-center gap-2 rounded-full px-3 py-1.5">
									<BadgeCheck className="size-4" />
									<span className="text-sm font-medium">Secure analytics access</span>
								</div>
								<h2 className="text-3xl font-semibold tracking-normal">{title}</h2>
								<p className="text-muted-foreground mt-2 text-sm leading-6">{subtitle}</p>
							</div>
							<div className="bg-background/50 mb-6 grid grid-cols-2 gap-1 rounded-xl border border-white/10 p-1">
								<Link
									href="/login"
									className={cn(
										'rounded-lg px-3 py-2 text-center text-sm font-medium transition',
										!isSignup
											? 'bg-primary text-primary-foreground shadow-soft'
											: 'text-muted-foreground hover:text-foreground'
									)}
								>
									Login
								</Link>
								<Link
									href="/signup"
									className={cn(
										'rounded-lg px-3 py-2 text-center text-sm font-medium transition',
										isSignup
											? 'bg-primary text-primary-foreground shadow-soft'
											: 'text-muted-foreground hover:text-foreground'
									)}
								>
									Create account
								</Link>
							</div>
							{children}
							<div className="text-muted-foreground mt-5 text-center text-sm">{footer}</div>
							<div className="text-muted-foreground mt-6 flex items-center justify-center gap-2 border-t border-white/10 pt-5 text-xs">
								<ChartNoAxesCombined className="text-primary size-4" />
								Your workspace opens after secure sign in.
							</div>
						</motion.div>
					</section>
				</div>
			</div>
		</main>
	);
}
