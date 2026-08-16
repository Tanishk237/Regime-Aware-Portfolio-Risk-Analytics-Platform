import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';
import type { HealthStatus, VersionInfo } from '@/lib/types';

import { keys } from './query-keys';

export function useHealth() {
	return useQuery({
		queryKey: keys.health,
		queryFn: () => api.get<HealthStatus>('/health'),
		retry: 0,
		refetchInterval: 60_000
	});
}

export function useVersion() {
	return useQuery({
		queryKey: keys.version,
		queryFn: () => api.get<VersionInfo>('/version'),
		retry: 0
	});
}
