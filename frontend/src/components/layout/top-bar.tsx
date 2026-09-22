'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { Bell, LogOut, Plus, RefreshCw, RotateCcw, Upload, User } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuSeparator,
	DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue
} from '@/components/ui/select';
import { SidebarTrigger } from '@/components/ui/sidebar';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { ThemeToggle } from '@/components/theme/theme-toggle';
import { useAuth } from '@/lib/auth';
import { useSelectedPortfolio } from '@/lib/portfolio-context';
import { useAlerts, useDemoPortfolio, useHealth, useRefreshIntelligence } from '@/lib/queries';
import { cn } from '@/lib/utils';

const ROUTE_LABELS: Record<string, string> = {
	'/dashboard': 'Dashboard',
	'/portfolios': 'Portfolios',
	'/trades': 'Trades',
	'/upload': 'Import',
	'/market': 'Market data',
	'/risk': 'Risk analytics',
	'/regime': 'Regime analytics',
	'/stress-tests': 'Stress tests',
	'/portfolio-health': 'Portfolio health',
	'/recommendations': 'Recommendations',
	'/ai-copilot': 'AI Copilot',
	'/settings': 'Settings'
};

export function PortfolioSelector({ className }: { className?: string }) {
	const { portfolios, isLoading, selectedId, select } = useSelectedPortfolio();
	const { user } = useAuth();

	if (user?.isGuest && portfolios.length === 0) {
		return (
			<Button asChild size="sm" variant="outline" className={className}>
				<Link href="/upload">
					<Plus className="size-3.5" /> Upload guest CSV
				</Link>
			</Button>
		);
	}

	if (isLoading) return <Skeleton className={cn('h-9 w-44', className)} />;

	if (portfolios.length === 0) {
		return (
			<div className={cn('flex items-center gap-2', className)}>
				<Button asChild size="sm" variant="outline">
					<Link href="/upload">
						<Upload className="size-3.5" /> Upload CSV
					</Link>
				</Button>
				<Button asChild size="sm" variant="ghost" className="hidden sm:inline-flex">
					<Link href="/portfolios">
						<Plus className="size-3.5" /> Create
					</Link>
				</Button>
			</div>
		);
	}

	return (
		<Select value={selectedId ?? ''} onValueChange={select}>
			<SelectTrigger
				className={cn('bg-card h-9 min-w-0 max-w-[11rem] sm:max-w-[14rem]', className)}
			>
				<SelectValue placeholder="Select portfolio" />
			</SelectTrigger>
			<SelectContent>
				{portfolios.map((portfolio) => (
					<SelectItem key={portfolio.id} value={portfolio.id}>
						{portfolio.name}
					</SelectItem>
				))}
			</SelectContent>
		</Select>
	);
}

function ApiStatus() {
	const { data, isLoading, isError, refetch } = useHealth();
	const state = isLoading ? 'checking' : isError ? 'offline' : 'online';
	const color =
		state === 'online' ? 'bg-positive' : state === 'offline' ? 'bg-negative' : 'bg-warning';

	return (
		<Tooltip>
			<TooltipTrigger asChild>
				<button
					type="button"
					onClick={() => void refetch()}
					className="bg-card flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-xs font-medium"
				>
					<span
						className={cn('size-2 rounded-full', color, state === 'checking' && 'animate-pulse')}
					/>
					<span className="hidden sm:inline">
						API {state === 'online' ? 'connected' : state === 'offline' ? 'offline' : 'checking'}
					</span>
				</button>
			</TooltipTrigger>
			<TooltipContent>
				{state === 'online'
					? `Backend reachable${data?.status ? ` · ${data.status}` : ''}`
					: 'Click to retry /health'}
			</TooltipContent>
		</Tooltip>
	);
}

export function TopBar() {
	const queryClient = useQueryClient();
	const { user, signOut } = useAuth();
	const { selected, select } = useSelectedPortfolio();
	const alerts = useAlerts(selected?.id);
	const unreadAlerts = (alerts.data ?? []).filter((item) => !item.is_read);
	const refreshIntelligence = useRefreshIntelligence(selected?.id);
	const demoPortfolio = useDemoPortfolio();
	const router = useRouter();
	const pathname = usePathname();
	const routeLabel =
		Object.entries(ROUTE_LABELS).find(([route]) =>
			pathname === route ? true : route !== '/dashboard' && pathname.startsWith(`${route}/`)
		)?.[1] ?? 'Workspace';
	const resetDemo = async () => {
		try {
			const result = await demoPortfolio.reset.mutateAsync();
			select(result.portfolio.id);
			toast.success('Demo portfolio reset');
			router.replace('/dashboard');
		} catch {
			toast.error('Could not reset the demo portfolio.');
		}
	};
	const refreshWorkspace = async () => {
		try {
			if (selected?.id) {
				await refreshIntelligence.mutateAsync();
				await Promise.all([
					queryClient.invalidateQueries({ queryKey: ['portfolio', selected.id] }),
					queryClient.invalidateQueries({ queryKey: ['risk', selected.id] }),
					queryClient.invalidateQueries({ queryKey: ['regime', selected.id] })
				]);
			} else {
				await queryClient.invalidateQueries();
			}
			toast.success('Analytics refreshed');
		} catch {
			toast.error('Could not refresh the workspace.');
		}
	};

	return (
		<header className="bg-background/88 sticky top-0 z-30 flex h-16 min-w-0 items-center gap-2 border-b px-3 shadow-[0_1px_0_color-mix(in_oklab,var(--border)_65%,transparent)] backdrop-blur-xl sm:px-5">
			<SidebarTrigger className="shrink-0" />
			<div className="min-w-0 flex-1">
				<div className="flex min-w-0 items-center gap-3">
					<PortfolioSelector />
					<div className="border-border/70 hidden min-w-0 items-center gap-2 border-l pl-3 lg:flex">
						<span className="bg-positive relative size-1.5 shrink-0 rounded-full">
							<span className="bg-positive absolute inset-0 rounded-full opacity-50 motion-safe:animate-ping" />
						</span>
						<span className="text-muted-foreground truncate text-xs">{routeLabel}</span>
					</div>
				</div>
			</div>
			<div className="ml-auto flex shrink-0 items-center gap-1.5 sm:gap-2">
				<Button
					variant="outline"
					size="sm"
					onClick={() => void refreshWorkspace()}
					disabled={refreshIntelligence.isPending}
				>
					<RefreshCw className="size-3.5" />
					<span className="hidden sm:inline">Refresh</span>
				</Button>
				<div className="hidden sm:block">
					<ApiStatus />
				</div>
				<DropdownMenu>
					<DropdownMenuTrigger asChild>
						<Button
							variant="ghost"
							size="icon"
							className="relative"
							aria-label={`Portfolio alerts, ${unreadAlerts.length} unread`}
						>
							<Bell className="size-4" />
							{unreadAlerts.length ? (
								<span className="bg-negative text-negative-foreground absolute right-0.5 top-0.5 flex size-4 items-center justify-center rounded-full text-[10px] font-medium">
									{Math.min(unreadAlerts.length, 9)}
								</span>
							) : null}
						</Button>
					</DropdownMenuTrigger>
					<DropdownMenuContent align="end" className="w-80">
						<DropdownMenuLabel>Portfolio alerts</DropdownMenuLabel>
						<DropdownMenuSeparator />
						{unreadAlerts.length ? (
							unreadAlerts.slice(0, 3).map((alert) => (
								<DropdownMenuItem key={alert.id} asChild className="items-start py-2.5">
									<Link href="/recommendations">
										<span className="min-w-0">
											<span className="block truncate text-sm font-medium">{alert.title}</span>
											<span className="text-muted-foreground mt-0.5 line-clamp-2 text-xs">
												{alert.evidence ?? alert.description}
											</span>
										</span>
									</Link>
								</DropdownMenuItem>
							))
						) : (
							<DropdownMenuItem disabled>No unread portfolio alerts</DropdownMenuItem>
						)}
						<DropdownMenuSeparator />
						<DropdownMenuItem asChild>
							<Link href="/recommendations">Open recommendation center</Link>
						</DropdownMenuItem>
					</DropdownMenuContent>
				</DropdownMenu>
				<ThemeToggle />
				<DropdownMenu>
					<DropdownMenuTrigger asChild>
						<Button variant="ghost" size="icon" aria-label="User menu">
							<span
								className={cn(
									'bg-primary text-primary-foreground flex size-7 items-center justify-center rounded-full text-xs font-semibold',
									user?.isGuest && 'bg-warning text-warning-foreground'
								)}
							>
								{(user?.name ?? 'D').slice(0, 1).toUpperCase()}
							</span>
						</Button>
					</DropdownMenuTrigger>
					<DropdownMenuContent align="end" className="w-56">
						<DropdownMenuLabel className="font-normal">
							<div className="flex items-center gap-2">
								<p className="text-sm font-medium">{user?.name ?? 'Demo User'}</p>
								{user?.isGuest ? (
									<span className="bg-warning-muted text-warning rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide">
										Guest
									</span>
								) : null}
							</div>
							<p className="text-muted-foreground text-xs">{user?.email ?? 'Signed in'}</p>
						</DropdownMenuLabel>
						<DropdownMenuSeparator />
						{selected?.is_demo ? (
							<DropdownMenuItem
								disabled={demoPortfolio.reset.isPending}
								onClick={() => void resetDemo()}
							>
								<RotateCcw className="size-4" />
								{demoPortfolio.reset.isPending ? 'Resetting demo...' : 'Reset demo portfolio'}
							</DropdownMenuItem>
						) : null}
						<DropdownMenuItem onClick={() => router.push('/settings')}>
							<User className="size-4" /> Settings
						</DropdownMenuItem>
						<DropdownMenuItem
							onClick={async () => {
								try {
									await signOut();
									await queryClient.cancelQueries();
									queryClient.clear();
									router.replace('/login');
								} catch {
									toast.error('Could not securely end this session. Please retry.');
								}
							}}
						>
							<LogOut className="size-4" /> {user?.isGuest ? 'Exit guest session' : 'Log out'}
						</DropdownMenuItem>
					</DropdownMenuContent>
				</DropdownMenu>
			</div>
		</header>
	);
}

export function PageHeader({
	title,
	description,
	actions
}: {
	title: string;
	description?: string;
	actions?: React.ReactNode;
}) {
	return (
		<div className="page-header-surface border-border/70 border-b pb-4 pt-1">
			<div className="flex flex-wrap items-end justify-between gap-3">
				<div>
					<h1 className="text-2xl font-semibold tracking-normal sm:text-[1.7rem]">{title}</h1>
					{description ? (
						<p className="text-muted-foreground mt-1 max-w-3xl text-sm leading-6">{description}</p>
					) : null}
				</div>
				{actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
			</div>
		</div>
	);
}
