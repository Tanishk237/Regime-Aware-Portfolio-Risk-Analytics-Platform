import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';
import type { HealthStatus, VersionInfo } from '@/lib/types';

import { keys } from './query-keys';

export function useHealth() {
	return useQuery({
		queryKey: keys.health,
		queryFn: ({ signal }) => api.get<HealthStatus>('/health', undefined, signal, 5_000),
		retry: 0,
		staleTime: 30_000,
		refetchInterval: 60_000,
		refetchIntervalInBackground: false
	});
}

export function useVersion() {
	return useQuery({
		queryKey: keys.version,
		queryFn: ({ signal }) => api.get<VersionInfo>('/version', undefined, signal, 5_000),
		retry: 0,
		staleTime: Number.POSITIVE_INFINITY
	});
}
