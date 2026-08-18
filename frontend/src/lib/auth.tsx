import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { login, logout, me, signup, type AuthResponse, type AuthUser } from '@/lib/api/auth';
import { AUTH_FAILURE_EVENT } from '@/lib/auth-events';
import { clearLegacyAccessToken } from '@/lib/storage';

const STORAGE_KEY = 'rapra.auth.user';

export type AppUser = {
	id: number;
	name: string;
	email: string;
};

function toAppUser(user: AuthUser): AppUser {
	return {
		id: user.id,
		name: user.full_name || user.email.split('@')[0] || 'User',
		email: user.email
	};
}

function read(): AppUser | null {
	if (typeof window === 'undefined') return null;
	try {
		const raw = window.localStorage.getItem(STORAGE_KEY);
		return raw ? (JSON.parse(raw) as AppUser) : null;
	} catch {
		return null;
	}
}

function clearStoredUser(): void {
	if (typeof window === 'undefined') return;
	window.localStorage.removeItem(STORAGE_KEY);
}

type AuthContextValue = {
	user: AppUser | null;
	hydrated: boolean;
	signIn: (input: { email: string; password: string }) => Promise<void>;
	signUp: (input: { name?: string; email: string; password: string }) => Promise<void>;
	signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
	const [user, setUser] = useState<AppUser | null>(null);
	const [hydrated, setHydrated] = useState(false);

	useEffect(() => {
		const storedUser = read();
		if (storedUser) setUser(storedUser);

		me()
			.then((freshUser) => {
				const next = toAppUser(freshUser);
				window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
				setUser(next);
			})
			.catch(() => {
				clearLegacyAccessToken();
				clearStoredUser();
				setUser(null);
			})
			.finally(() => setHydrated(true));
	}, []);

	useEffect(() => {
		const handleAuthFailure = () => {
			clearLegacyAccessToken();
			clearStoredUser();
			setUser(null);
		};
		window.addEventListener(AUTH_FAILURE_EVENT, handleAuthFailure);
		return () => window.removeEventListener(AUTH_FAILURE_EVENT, handleAuthFailure);
	}, []);

	const persistAuth = useCallback((response: AuthResponse) => {
		clearLegacyAccessToken();
		const next = toAppUser(response.user);
		window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
		setUser(next);
	}, []);

	const signIn = useCallback(
		async (input: { email: string; password: string }) => {
			persistAuth(await login(input));
		},
		[persistAuth]
	);

	const signUp = useCallback(
		async (input: { name?: string; email: string; password: string }) => {
			persistAuth(
				await signup({
					email: input.email,
					password: input.password,
					full_name: input.name
				})
			);
		},
		[persistAuth]
	);

	const signOut = useCallback(async () => {
		try {
			await logout();
		} catch {
			// Local cleanup still happens if the backend is unreachable.
		}
		clearLegacyAccessToken();
		clearStoredUser();
		setUser(null);
	}, []);

	const value = useMemo(
		() => ({ user, hydrated, signIn, signUp, signOut }),
		[user, hydrated, signIn, signUp, signOut]
	);
	return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
	const ctx = useContext(AuthContext);
	if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
	return ctx;
}
