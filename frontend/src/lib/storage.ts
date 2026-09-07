export const GUEST_STORAGE_KEY = 'rapra.auth.guest';
export const GUEST_TOKEN_STORAGE_KEY = 'rapra.auth.guestToken';
export const SESSION_USER_STORAGE_KEY = 'rapra.auth.sessionUser';

export function clearRapraLocalStorage(): void {
	if (typeof window === 'undefined') return;

	for (const key of Object.keys(window.localStorage)) {
		if (key.startsWith('rapra.')) window.localStorage.removeItem(key);
	}
}

export function clearRapraSessionStorage(): void {
	if (typeof window === 'undefined') return;

	for (const key of Object.keys(window.sessionStorage)) {
		if (key.startsWith('rapra.')) window.sessionStorage.removeItem(key);
	}
}

export function clearLegacyAccessToken(): void {
	if (typeof window === 'undefined') return;
	window.localStorage.removeItem('rapra.auth.accessToken');
}

export function getGuestAccessToken(): string | null {
	if (typeof window === 'undefined') return null;
	return window.sessionStorage.getItem(GUEST_TOKEN_STORAGE_KEY);
}
