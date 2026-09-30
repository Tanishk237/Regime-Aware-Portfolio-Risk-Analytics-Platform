import type { RiskAnalytics } from '@/lib/types';

// Missing, blank, and boolean inputs must never become reassuring zeroes.
export function metric(risk: RiskAnalytics | undefined, ...names: string[]): number | undefined {
	const metrics = risk?.metrics;
	if (!metrics) return undefined;
	for (const name of names) {
		const entry = Object.entries(metrics).find(([key]) => key.toLowerCase() === name.toLowerCase());
		const value = entry?.[1];
		if (typeof value === 'number' && Number.isFinite(value)) return value;
	}
	return undefined;
}
