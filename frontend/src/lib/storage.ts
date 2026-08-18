export function clearRapraLocalStorage(): void {
	if (typeof window === 'undefined') return;

	for (const key of Object.keys(window.localStorage)) {
		if (key.startsWith('rapra.')) window.localStorage.removeItem(key);
	}
}

export function clearLegacyAccessToken(): void {
	if (typeof window === 'undefined') return;
	window.localStorage.removeItem('rapra.auth.accessToken');
}
