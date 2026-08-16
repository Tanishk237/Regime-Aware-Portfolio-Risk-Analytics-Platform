'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Loader2 } from 'lucide-react';

import { AppSidebar } from '@/components/layout/app-sidebar';
import { TopBar } from '@/components/layout/top-bar';
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
			<SidebarProvider>
				<div className="flex min-h-screen w-full">
					<AppSidebar />
					<SidebarInset className="app-shell min-w-0">
						<TopBar />
						<main className="mx-auto min-w-0 flex-1 space-y-5 p-3 sm:p-4 lg:max-w-[1480px] lg:p-6">
							{children}
						</main>
					</SidebarInset>
				</div>
			</SidebarProvider>
		</SelectedPortfolioProvider>
	);
}
