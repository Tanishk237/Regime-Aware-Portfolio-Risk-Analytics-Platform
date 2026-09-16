'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { ThemeProvider } from '@/components/theme/theme-provider';
import { AuthProvider } from '@/lib/auth';
import { AUTH_FAILURE_EVENT } from '@/lib/auth-events';
import { ApiError } from '@/lib/api';

export function RootProviders({ children }: { children: React.ReactNode }) {
	const [queryClient] = useState(
		() =>
			new QueryClient({
				defaultOptions: {
					queries: {
						staleTime: 30_000,
						gcTime: 5 * 60_000,
						refetchOnWindowFocus: false,
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
		return () => window.removeEventListener(AUTH_FAILURE_EVENT, clearClient);
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
