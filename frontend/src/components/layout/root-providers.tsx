'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { AuthProvider } from '@/lib/auth';
import { AUTH_FAILURE_EVENT } from '@/lib/auth-events';

export function RootProviders({ children }: { children: React.ReactNode }) {
	const [queryClient] = useState(
		() =>
			new QueryClient({
				defaultOptions: {
					queries: {
						staleTime: 30_000,
						refetchOnWindowFocus: false,
						retry: 1
					}
				}
			})
	);

	useEffect(() => {
		const clearClient = () => {
			queryClient.cancelQueries();
			queryClient.clear();
		};
		window.addEventListener(AUTH_FAILURE_EVENT, clearClient);
		return () => window.removeEventListener(AUTH_FAILURE_EVENT, clearClient);
	}, [queryClient]);

	return (
		<QueryClientProvider client={queryClient}>
			<AuthProvider>
				<TooltipProvider delayDuration={200}>
					{children}
					<Toaster richColors position="top-right" />
				</TooltipProvider>
			</AuthProvider>
		</QueryClientProvider>
	);
}
