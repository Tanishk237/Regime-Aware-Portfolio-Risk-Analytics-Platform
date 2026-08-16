'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { LogOut, Moon, Plus, RefreshCw, Sun, User } from 'lucide-react';
import { useEffect, useState } from 'react';
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
import { useAuth } from '@/lib/auth';
import { useSelectedPortfolio } from '@/lib/portfolio-context';
import { useHealth } from '@/lib/queries';
import { cn } from '@/lib/utils';

export function PortfolioSelector({ className }: { className?: string }) {
	const { portfolios, isLoading, selectedId, select } = useSelectedPortfolio();

	if (isLoading) return <Skeleton className={cn('h-9 w-44', className)} />;

	if (portfolios.length === 0) {
		return (
			<Button asChild size="sm" variant="outline" className={className}>
				<Link href="/portfolios">
					<Plus className="size-3.5" /> Create your first portfolio
				</Link>
			</Button>
		);
	}

	return (
		<Select value={selectedId ?? ''} onValueChange={select}>
			<SelectTrigger className={cn('bg-card h-9 w-[190px]', className)}>
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

function ThemeToggle() {
	const [dark, setDark] = useState(false);
	useEffect(() => {
		const stored = window.localStorage.getItem('rapra.theme') === 'dark';
		setDark(stored);
		document.documentElement.classList.toggle('dark', stored);
	}, []);

	return (
		<Button
			variant="ghost"
			size="icon"
			aria-label="Toggle theme"
			onClick={() => {
				const next = !dark;
				setDark(next);
				document.documentElement.classList.toggle('dark', next);
				window.localStorage.setItem('rapra.theme', next ? 'dark' : 'light');
			}}
		>
			{dark ? <Moon className="size-4" /> : <Sun className="size-4" />}
		</Button>
	);
}

export function TopBar() {
	const queryClient = useQueryClient();
	const { user, signOut } = useAuth();
	const router = useRouter();

	return (
		<header className="bg-background/92 sticky top-0 z-30 flex h-14 items-center gap-2 border-b px-3 shadow-[0_1px_0_color-mix(in_oklab,var(--border)_65%,transparent)] backdrop-blur sm:px-4">
			<SidebarTrigger />
			<PortfolioSelector />
			<div className="ml-auto flex items-center gap-1.5 sm:gap-2">
				<Button
					variant="outline"
					size="sm"
					onClick={async () => {
						await queryClient.invalidateQueries();
						toast.success('Analytics refreshed');
					}}
				>
					<RefreshCw className="size-3.5" />
					<span className="hidden sm:inline">Refresh</span>
				</Button>
				<ApiStatus />
				<ThemeToggle />
				<DropdownMenu>
					<DropdownMenuTrigger asChild>
						<Button variant="ghost" size="icon" aria-label="User menu">
							<span className="bg-primary text-primary-foreground flex size-7 items-center justify-center rounded-full text-xs font-semibold">
								{(user?.name ?? 'D').slice(0, 1).toUpperCase()}
							</span>
						</Button>
					</DropdownMenuTrigger>
					<DropdownMenuContent align="end" className="w-56">
						<DropdownMenuLabel className="font-normal">
							<p className="text-sm font-medium">{user?.name ?? 'Demo User'}</p>
							<p className="text-muted-foreground text-xs">{user?.email ?? 'Signed in'}</p>
						</DropdownMenuLabel>
						<DropdownMenuSeparator />
						<DropdownMenuItem onClick={() => router.push('/settings')}>
							<User className="size-4" /> Settings
						</DropdownMenuItem>
						<DropdownMenuItem
							onClick={async () => {
								await queryClient.cancelQueries();
								queryClient.clear();
								signOut();
								router.replace('/login');
							}}
						>
							<LogOut className="size-4" /> Log out
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
		<div className="flex flex-wrap items-end justify-between gap-3 border-b pb-4">
			<div>
				<h1 className="text-xl font-semibold">{title}</h1>
				{description ? <p className="text-muted-foreground mt-0.5 text-sm">{description}</p> : null}
			</div>
			{actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
		</div>
	);
}
