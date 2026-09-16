'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Loader2 } from 'lucide-react';

import { AppSidebar } from '@/components/layout/app-sidebar';
import { TopBar } from '@/components/layout/top-bar';
import { PageTransition } from '@/components/motion/page-transition';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';
import { useAuth } from '@/lib/auth';
import { SelectedPortfolioProvider } from '@/lib/portfolio-context';

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
	const router = useRouter();
	const { user, hydrated } = useAuth();

	useEffect(() => {
		if (hydrated && !user) router.replace('/login');
	}, [hydrated, router, user]);

	if (!hydrated || !user) {
		return (
			<main className="bg-surface flex min-h-screen items-center justify-center">
				<Loader2 className="text-muted-foreground size-5 animate-spin" />
			</main>
		);
	}

	return (
		<SelectedPortfolioProvider>
			<SidebarProvider className="min-h-screen overflow-x-hidden">
				<AppSidebar />
				<SidebarInset className="app-shell w-auto min-w-0 flex-1 overflow-x-hidden">
					<TopBar />
					<main className="mx-auto w-full min-w-0 max-w-[1480px] flex-1 space-y-6 overflow-x-hidden p-4 sm:p-5 lg:p-7">
						<PageTransition>{children}</PageTransition>
					</main>
				</SidebarInset>
			</SidebarProvider>
		</SelectedPortfolioProvider>
	);
}
