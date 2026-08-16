export function clearRapraLocalStorage(): void {
	if (typeof window === 'undefined') return;

	for (const key of Object.keys(window.localStorage)) {
		if (key.startsWith('rapra.')) window.localStorage.removeItem(key);
	}
}
