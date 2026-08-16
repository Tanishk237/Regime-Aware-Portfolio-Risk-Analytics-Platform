export function formatCurrency(value?: number | null, currency = 'INR', compact = false) {
	if (value === null || value === undefined || Number.isNaN(value)) return '—';
	try {
		return new Intl.NumberFormat('en-IN', {
			style: 'currency',
			currency: currency || 'INR',
			maximumFractionDigits: compact ? 1 : 2,
			minimumFractionDigits: compact ? 0 : 2,
			notation: compact ? 'compact' : 'standard'
		}).format(value);
	} catch {
		return `${value.toFixed(2)}`;
	}
}

export function formatNumber(value?: number | null, digits = 2) {
	if (value === null || value === undefined || Number.isNaN(value)) return '—';
	return new Intl.NumberFormat('en-IN', {
		minimumFractionDigits: digits,
		maximumFractionDigits: digits
	}).format(value);
}

/** Percent formatter. `fraction` = true when input is 0.1234 rather than 12.34. */
export function formatPercent(value?: number | null, fraction = true, digits = 2) {
	if (value === null || value === undefined || Number.isNaN(value)) return '—';
	const pct = fraction ? value * 100 : value;
	return `${pct >= 0 ? '' : ''}${pct.toFixed(digits)}%`;
}

export function formatRisk(value?: number | null, digits = 4) {
	if (value === null || value === undefined || Number.isNaN(value)) return '—';
	return value.toFixed(digits);
}

export function formatDate(value?: string | null) {
	if (!value) return '—';
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return value;
	return new Intl.DateTimeFormat('en-IN', {
		day: '2-digit',
		month: 'short',
		year: 'numeric'
	}).format(date);
}

export function formatDateTime(value?: string | null) {
	if (!value) return '—';
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return value;
	return new Intl.DateTimeFormat('en-IN', {
		day: '2-digit',
		month: 'short',
		year: 'numeric',
		hour: '2-digit',
		minute: '2-digit'
	}).format(date);
}

export function isoDate(date: Date) {
	return date.toISOString().slice(0, 10);
}

export function daysAgo(days: number) {
	const d = new Date();
	d.setDate(d.getDate() - days);
	return isoDate(d);
}

export function signClass(value?: number | null) {
	if (value === null || value === undefined || Number.isNaN(value) || value === 0)
		return 'text-muted-foreground';
	return value > 0 ? 'text-positive' : 'text-negative';
}

/** Normalises a series that may arrive as a date->value map or as an array. */
export function toSeries(
	input?: Record<string, number> | Array<{ date: string; value: number }> | null
): Array<{ date: string; value: number }> {
	if (!input) return [];
	if (Array.isArray(input)) {
		return input
			.filter((d) => d && d.date !== undefined)
			.map((d) => ({ date: String(d.date), value: Number(d.value) }));
	}
	return Object.entries(input)
		.map(([date, value]) => ({ date, value: Number(value) }))
		.sort((a, b) => (a.date < b.date ? -1 : 1));
}

export function shortDate(value: string) {
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return value;
	return new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short' }).format(date);
}
