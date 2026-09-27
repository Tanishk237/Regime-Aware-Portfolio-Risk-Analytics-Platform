'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { ThemeProvider } from '@/components/theme/theme-provider';
import { AuthProvider } from '@/lib/auth';
import { AUTH_FAILURE_EVENT, PRINCIPAL_CHANGED_EVENT } from '@/lib/auth-events';
import { ApiError } from '@/lib/api';

export function RootProviders({ children }: { children: React.ReactNode }) {
	const [queryClient] = useState(
		() =>
			new QueryClient({
				defaultOptions: {
					queries: {
						staleTime: 2 * 60_000,
						gcTime: 15 * 60_000,
						refetchOnWindowFocus: false,
						refetchOnReconnect: true,
						retryDelay: (attemptIndex) => Math.min(500 * 2 ** attemptIndex, 4_000),
						retry: (failureCount, error) => {
							if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
								return error.status === 408 || error.status === 429 ? failureCount < 1 : false;
							}
							return failureCount < 1;
						}
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
		window.addEventListener(PRINCIPAL_CHANGED_EVENT, clearClient);
		return () => {
			window.removeEventListener(AUTH_FAILURE_EVENT, clearClient);
			window.removeEventListener(PRINCIPAL_CHANGED_EVENT, clearClient);
		};
	}, [queryClient]);

	return (
		<ThemeProvider>
			<QueryClientProvider client={queryClient}>
				<AuthProvider>
					<TooltipProvider delayDuration={200}>
						{children}
						<Toaster richColors position="top-right" />
					</TooltipProvider>
				</AuthProvider>
			</QueryClientProvider>
		</ThemeProvider>
	);
}
