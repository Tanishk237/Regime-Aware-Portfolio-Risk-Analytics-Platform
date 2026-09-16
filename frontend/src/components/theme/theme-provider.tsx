'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

export type Theme = 'dark' | 'light';

const THEME_STORAGE_KEY = 'latent.theme';
const LEGACY_THEME_STORAGE_KEY = 'rapra.theme';

type ThemeContextValue = {
	theme: Theme;
	setTheme: (theme: Theme) => void;
	toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function applyTheme(theme: Theme) {
	document.documentElement.classList.toggle('dark', theme === 'dark');
	document.documentElement.style.colorScheme = theme;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
	const [theme, setThemeState] = useState<Theme>('dark');

	useEffect(() => {
		const stored =
			window.localStorage.getItem(THEME_STORAGE_KEY) ??
			window.localStorage.getItem(LEGACY_THEME_STORAGE_KEY);
		const initialTheme: Theme = stored === 'light' ? 'light' : 'dark';
		setThemeState(initialTheme);
		applyTheme(initialTheme);
	}, []);

	const setTheme = useCallback((nextTheme: Theme) => {
		setThemeState(nextTheme);
		window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
		window.localStorage.removeItem(LEGACY_THEME_STORAGE_KEY);
		applyTheme(nextTheme);
	}, []);

	const value = useMemo(
		() => ({
			theme,
			setTheme,
			toggleTheme: () => setTheme(theme === 'dark' ? 'light' : 'dark')
		}),
		[setTheme, theme]
	);

	return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
	const context = useContext(ThemeContext);
	if (!context) throw new Error('useTheme must be used inside ThemeProvider');
	return context;
}
