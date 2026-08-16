/**
 * Central API client for the Regime Aware Portfolio Risk Analytics backend.
 *
 * Base URL is configurable via NEXT_PUBLIC_API_BASE_URL.
 */

import { isAuthFailure, publishAuthFailure } from '@/lib/auth-events';

export const API_BASE_URL = (
	process.env['NEXT_PUBLIC_API_BASE_URL'] ?? 'http://localhost:8000/api/v1'
).replace(/\/$/, '');

export type ApiErrorShape = {
	code?: string;
	message?: string;
	details?: unknown;
};

const FRIENDLY_ERRORS: Record<string, string> = {
	PORTFOLIO_NOT_FOUND: 'Portfolio not found.',
	TRADE_NOT_FOUND: 'Trade not found.',
	CSV_MISSING_COLUMNS: 'CSV is missing required columns.',
	INVALID_TRADE_CSV: 'CSV contains invalid trade data.',
	MARKET_DATA_UNAVAILABLE:
		'Market data provider is temporarily unavailable. Stored data may be used if available.',
	MARKET_DATA_EMPTY: 'No market data was found for this request.',
	FII_DII_FILE_NOT_FOUND: 'FII/DII data source is not configured.',
	PORTFOLIO_RETURNS_EMPTY: 'Portfolio returns are not available yet.',
	INSUFFICIENT_MARKET_DATA: 'Not enough market data to calculate analytics.',
	PORTFOLIO_POSITIONS_EMPTY: 'This portfolio has no open positions.',
	INVALID_DATE_RANGE: 'End date must be after start date.',
	WEIGHTS_TICKERS_MISMATCH: 'Weights must match the number of tickers.',
	AUTH_REQUIRED: 'Please log in to continue.',
	INVALID_LOGIN: 'Invalid email or password.',
	INVALID_AUTH_TOKEN: 'Your session is invalid. Please log in again.',
	TOKEN_EXPIRED: 'Your session expired. Please log in again.',
	EMAIL_ALREADY_REGISTERED: 'An account with this email already exists.',
	USER_DISABLED: 'This account is disabled.'
};

export class ApiError extends Error {
	code: string;
	status: number;
	details: unknown;

	constructor(opts: {
		code?: string | undefined;
		message?: string | undefined;
		status?: number | undefined;
		details?: unknown;
	}) {
		const code = opts.code ?? 'REQUEST_FAILED';
		super(FRIENDLY_ERRORS[code] ?? opts.message ?? 'Something went wrong talking to the backend.');
		this.name = 'ApiError';
		this.code = code;
		this.status = opts.status ?? 0;
		this.details = opts.details;
	}
}

export type QueryParams = Record<string, string | number | boolean | undefined | null>;

function buildUrl(path: string, params?: QueryParams) {
	const url = `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
	if (!params) return url;
	const search = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value === undefined || value === null || value === '') continue;
		search.set(key, String(value));
	}
	const qs = search.toString();
	return qs ? `${url}?${qs}` : url;
}

async function parse<T>(response: Response): Promise<T> {
	const text = await response.text();
	let json: unknown = undefined;
	if (text) {
		try {
			json = JSON.parse(text);
		} catch {
			json = undefined;
		}
	}

	const body = json as { success?: boolean; error?: ApiErrorShape; data?: unknown } | undefined;

	if (!response.ok || body?.success === false) {
		const error = new ApiError({
			code: body?.error?.code,
			message: body?.error?.message ?? response.statusText,
			status: response.status,
			details: body?.error?.details
		});
		if (isAuthFailure(error.status, error.code)) publishAuthFailure();
		throw error;
	}

	// Backends commonly wrap payloads as { success: true, data: ... }
	if (body && typeof body === 'object' && 'data' in body && 'success' in body) {
		return body.data as T;
	}
	return body as T;
}

async function request<T>(
	method: string,
	path: string,
	opts: {
		params?: QueryParams | undefined;
		body?: unknown;
		formData?: FormData | undefined;
		signal?: AbortSignal | undefined;
	} = {}
): Promise<T> {
	let response: Response;
	try {
		const init: RequestInit = {
			method,
			credentials: 'include'
		};
		if (opts.signal) init.signal = opts.signal;
		if (opts.formData) {
			init.body = opts.formData;
		} else {
			init.headers = { 'Content-Type': 'application/json' };
			if (opts.body !== undefined) init.body = JSON.stringify(opts.body);
		}
		response = await fetch(buildUrl(path, opts.params), init);
	} catch (error) {
		throw new ApiError({
			code: 'NETWORK_ERROR',
			message:
				error instanceof Error && error.name === 'AbortError'
					? 'Request cancelled.'
					: `Cannot reach the backend at ${API_BASE_URL}.`
		});
	}
	return parse<T>(response);
}

export const api = {
	get: <T>(path: string, params?: QueryParams, signal?: AbortSignal) =>
		request<T>('GET', path, { params, signal }),
	post: <T>(path: string, body?: unknown, params?: QueryParams) =>
		request<T>('POST', path, { body, params }),
	put: <T>(path: string, body?: unknown) => request<T>('PUT', path, { body }),
	del: <T>(path: string) => request<T>('DELETE', path),
	upload: <T>(path: string, formData: FormData) => request<T>('POST', path, { formData })
};

export function errorMessage(error: unknown): string {
	if (error instanceof ApiError) return error.message;
	if (error instanceof Error) return error.message;
	return 'Unexpected error.';
}
