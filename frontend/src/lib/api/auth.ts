import { api } from '@/lib/api';

export type AuthUser = {
	id: number;
	email: string;
	full_name?: string | null;
	is_active: boolean;
	created_at: string;
	updated_at: string;
};

export type AuthResponse = {
	access_token: string;
	token_type: 'bearer';
	expires_in: number;
	user: AuthUser;
};

export function login(input: { email: string; password: string }) {
	return api.post<AuthResponse>('/auth/login', input);
}

export function signup(input: { email: string; password: string; full_name?: string }) {
	return api.post<AuthResponse>('/auth/signup', input);
}

export function me() {
	return api.get<AuthUser>('/auth/me');
}

export function logout() {
	return api.post<void>('/auth/logout');
}
