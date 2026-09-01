import type { PortfolioReturn, SeriesPoint } from '@/lib/types';

function isFinitePoint(point: SeriesPoint) {
	return point.date && Number.isFinite(point.value);
}

export function cumulativeSeriesFromReturns(returns: PortfolioReturn[] = []): SeriesPoint[] {
	let cumulative = 1;
	const points = returns.map((row) => {
		if (row.cumulative_return === null || row.cumulative_return === undefined) {
			cumulative *= 1 + Number(row.daily_return ?? 0);
			return { date: row.date, value: cumulative - 1 };
		}
		cumulative = 1 + Number(row.cumulative_return);
		return { date: row.date, value: Number(row.cumulative_return) };
	});

	return points.filter(isFinitePoint);
}

export function dailySeriesFromReturns(returns: PortfolioReturn[] = []): SeriesPoint[] {
	return returns
		.map((row) => ({ date: row.date, value: Number(row.daily_return) }))
		.filter(isFinitePoint);
}

export function drawdownSeriesFromCumulative(cumulativeReturns: SeriesPoint[] = []): SeriesPoint[] {
	let peak = 1;
	return cumulativeReturns
		.map((point) => {
			const portfolioValue = 1 + point.value;
			peak = Math.max(peak, portfolioValue);
			return {
				date: point.date,
				value: peak > 0 ? portfolioValue / peak - 1 : 0
			};
		})
		.filter(isFinitePoint);
}
