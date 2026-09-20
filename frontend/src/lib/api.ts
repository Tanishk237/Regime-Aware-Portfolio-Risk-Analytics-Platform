/**
 * Central API client for the Latent backend.
 *
 * Base URL is configurable via NEXT_PUBLIC_API_BASE_URL.
 */

import { isAuthFailure, publishAuthFailure } from '@/lib/auth-events';
import { getGuestAccessToken } from '@/lib/storage';

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
	MARKET_DATA_INCOMPLETE:
		'The provider is unavailable and stored data does not cover the full requested range.',
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
	SESSION_REVOKED: 'This session was signed out. Please log in again.',
	EMAIL_ALREADY_REGISTERED: 'An account with this email already exists.',
	USER_DISABLED: 'This account is disabled.',
	RATE_LIMITED: 'Too many requests. Wait a moment and try again.',
	PORTFOLIO_LIMIT_REACHED: 'Your portfolio limit is reached. Delete one before creating another.',
	PORTFOLIO_TRADE_LIMIT_REACHED: 'This portfolio has reached its trade limit.',
	CSV_TOO_MANY_ROWS: 'CSV has too many trade rows.',
	CSV_TOO_MANY_COLUMNS: 'CSV has too many columns.',
	CSV_TOO_MANY_CELLS: 'CSV is too large to process safely.',
	CSV_FIELD_TOO_LONG: 'CSV contains a field that is too long.',
	REQUEST_TOO_LARGE: 'This upload is larger than the server limit.',
	AI_API_KEY_REQUIRED: 'Add a valid AI provider key first.',
	AI_PROMPT_REQUIRED: 'Enter a prompt before asking the copilot.',
	AI_PROVIDER_ERROR: 'The selected AI provider rejected the request. Check the key and provider.',
	AI_PROVIDER_UNAVAILABLE: 'The selected AI provider is temporarily unavailable.',
	AI_PROVIDER_INVALID_RESPONSE: 'The selected AI provider returned an unexpected response.',
	STRESS_CONFIRMATION_REQUIRED: 'Confirm the parsed scenario before running it.',
	STRESS_VALUE_UNAVAILABLE: 'A complete portfolio valuation is required for this stress test.',
	STRESS_POSITION_VALUE_UNAVAILABLE:
		'Every open position needs a current value before stress testing.',
	REQUEST_TIMEOUT: 'The request took too long. Please retry.'
};

const configuredTimeout = Number(process.env['NEXT_PUBLIC_API_TIMEOUT_MS'] ?? 60_000);
const API_TIMEOUT_MS =
	Number.isFinite(configuredTimeout) && configuredTimeout > 0 ? configuredTimeout : 60_000;

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
	const controller = new AbortController();
	let timedOut = false;
	const abortFromCaller = () => controller.abort();
	if (opts.signal?.aborted) controller.abort();
	else if (opts.signal) opts.signal.addEventListener('abort', abortFromCaller, { once: true });
	const timeout = globalThis.setTimeout(() => {
		timedOut = true;
		controller.abort();
	}, API_TIMEOUT_MS);
	try {
		const init: RequestInit = {
			method,
			credentials: 'include',
			signal: controller.signal
		};
		if (opts.formData) {
			const guestToken = getGuestAccessToken();
			if (guestToken) init.headers = { Authorization: `Bearer ${guestToken}` };
			init.body = opts.formData;
		} else {
			const guestToken = getGuestAccessToken();
			init.headers = {
				'Content-Type': 'application/json',
				...(guestToken ? { Authorization: `Bearer ${guestToken}` } : {})
			};
			if (opts.body !== undefined) init.body = JSON.stringify(opts.body);
		}
		const response = await fetch(buildUrl(path, opts.params), init);
		return await parse<T>(response);
	} catch (error) {
		if (error instanceof ApiError) throw error;
		throw new ApiError({
			code: timedOut ? 'REQUEST_TIMEOUT' : 'NETWORK_ERROR',
			message: timedOut
				? 'The backend request timed out.'
				: error instanceof Error && error.name === 'AbortError'
					? 'Request cancelled.'
					: `Cannot reach the backend at ${API_BASE_URL}.`
		});
	} finally {
		globalThis.clearTimeout(timeout);
		if (opts.signal) opts.signal.removeEventListener('abort', abortFromCaller);
	}
}

export const api = {
	get: <T>(path: string, params?: QueryParams, signal?: AbortSignal) =>
		request<T>('GET', path, { params, signal }),
	post: <T>(path: string, body?: unknown, params?: QueryParams) =>
		request<T>('POST', path, { body, params }),
	put: <T>(path: string, body?: unknown) => request<T>('PUT', path, { body }),
	patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, { body }),
	del: <T>(path: string, body?: unknown) => request<T>('DELETE', path, { body }),
	upload: <T>(path: string, formData: FormData) => request<T>('POST', path, { formData })
};

export function errorMessage(error: unknown): string {
	if (error instanceof ApiError) return error.message;
	if (error instanceof Error) return error.message;
	return 'Unexpected error.';
}
