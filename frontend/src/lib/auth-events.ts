import { clearLegacyAccessToken } from '@/lib/storage';

export const AUTH_FAILURE_EVENT = 'rapra:auth-failure';

const AUTH_FAILURE_CODES = new Set([
	'AUTH_REQUIRED',
	'INVALID_AUTH_TOKEN',
	'TOKEN_EXPIRED',
	'USER_NOT_FOUND',
	'USER_DISABLED'
]);

export function isAuthFailure(status: number, code?: string): boolean {
	return status === 401 || Boolean(code && AUTH_FAILURE_CODES.has(code));
}

export function publishAuthFailure(): void {
	if (typeof window === 'undefined') return;
	clearLegacyAccessToken();
	window.dispatchEvent(new Event(AUTH_FAILURE_EVENT));
}
