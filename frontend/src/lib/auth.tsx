import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import {
	createGuestSession,
	login,
	logout,
	me,
	signup,
	type AuthResponse,
	type AuthUser
} from '@/lib/api/auth';
import { AUTH_FAILURE_EVENT } from '@/lib/auth-events';
import {
	clearLegacyAccessToken,
	clearRapraSessionStorage,
	getGuestAccessToken,
	GUEST_STORAGE_KEY,
	GUEST_TOKEN_STORAGE_KEY,
	SESSION_USER_STORAGE_KEY
} from '@/lib/storage';

const STORAGE_KEY = 'rapra.auth.user';

export type AppUser = {
	id: number;
	name: string;
	email: string;
	isGuest?: boolean;
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

function readGuest(): AppUser | null {
	if (typeof window === 'undefined') return null;
	try {
		const raw = window.sessionStorage.getItem(GUEST_STORAGE_KEY);
		return raw ? (JSON.parse(raw) as AppUser) : null;
	} catch {
		return null;
	}
}

function readSessionUser(): AppUser | null {
	if (typeof window === 'undefined') return null;
	try {
		const raw = window.sessionStorage.getItem(SESSION_USER_STORAGE_KEY);
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
	signIn: (input: { email: string; password: string; rememberMe?: boolean }) => Promise<void>;
	signUp: (input: { name?: string; email: string; password: string }) => Promise<void>;
	continueAsGuest: () => Promise<void>;
	signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
	const [user, setUser] = useState<AppUser | null>(null);
	const [hydrated, setHydrated] = useState(false);

	useEffect(() => {
		const guestUser = readGuest();
		if (guestUser && getGuestAccessToken()) {
			setUser({ ...guestUser, isGuest: true });
			setHydrated(true);
			return;
		}

		const storedUser = read();
		const sessionUser = readSessionUser();
		const existingUser = storedUser ?? sessionUser;
		if (!existingUser) {
			setHydrated(true);
			return;
		}
		setUser(existingUser);

		me()
			.then((freshUser) => {
				const next = toAppUser(freshUser);
				if (storedUser) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
				else window.sessionStorage.setItem(SESSION_USER_STORAGE_KEY, JSON.stringify(next));
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
			clearRapraSessionStorage();
			setUser(null);
		};
		window.addEventListener(AUTH_FAILURE_EVENT, handleAuthFailure);
		return () => window.removeEventListener(AUTH_FAILURE_EVENT, handleAuthFailure);
	}, []);

	const persistAuth = useCallback((response: AuthResponse, rememberMe = false) => {
		clearLegacyAccessToken();
		clearRapraSessionStorage();
		const next = toAppUser(response.user);
		if (rememberMe) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
		else window.sessionStorage.setItem(SESSION_USER_STORAGE_KEY, JSON.stringify(next));
		setUser(next);
	}, []);

	const signIn = useCallback(
		async (input: { email: string; password: string; rememberMe?: boolean }) => {
			const rememberMe = Boolean(input.rememberMe);
			persistAuth(
				await login({
					email: input.email,
					password: input.password,
					remember_me: rememberMe
				}),
				rememberMe
			);
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

	const continueAsGuest = useCallback(async () => {
		clearLegacyAccessToken();
		clearStoredUser();
		clearRapraSessionStorage();
		const response = await createGuestSession();
		const next: AppUser = {
			...toAppUser(response.user),
			name: 'Guest',
			email: 'Session-only guest',
			isGuest: true
		};
		window.sessionStorage.setItem(GUEST_TOKEN_STORAGE_KEY, response.access_token);
		window.sessionStorage.setItem(GUEST_STORAGE_KEY, JSON.stringify(next));
		setUser(next);
	}, []);

	const signOut = useCallback(async () => {
		if (!user?.isGuest) {
			try {
				await logout();
			} catch {
				// Local cleanup still happens if the backend is unreachable.
			}
		}
		clearLegacyAccessToken();
		clearStoredUser();
		clearRapraSessionStorage();
		setUser(null);
	}, [user?.isGuest]);

	const value = useMemo(
		() => ({ user, hydrated, signIn, signUp, continueAsGuest, signOut }),
		[user, hydrated, signIn, signUp, continueAsGuest, signOut]
	);
	return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
	const ctx = useContext(AuthContext);
	if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
	return ctx;
}
