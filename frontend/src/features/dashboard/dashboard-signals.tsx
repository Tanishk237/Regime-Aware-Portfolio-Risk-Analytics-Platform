import { useId, useMemo } from 'react';

import type { SeriesPoint } from '@/lib/types';
import { cn } from '@/lib/utils';

type Point = { x: number; y: number };

const REGIME_STATES = ['Bull', 'Bear', 'High vol', 'Crisis'] as const;

function smoothPath(points: Point[]) {
	const first = points[0];
	if (!first || points.length < 2) return '';
	let path = `M ${first.x.toFixed(2)} ${first.y.toFixed(2)}`;

	for (let index = 0; index < points.length - 1; index += 1) {
		const current = points[index];
		const next = points[index + 1];
		if (!current || !next) continue;
		const previous = points[index - 1] ?? current;
		const afterNext = points[index + 2] ?? next;
		const controlOne = {
			x: current.x + (next.x - previous.x) / 6,
			y: current.y + (next.y - previous.y) / 6
		};
		const controlTwo = {
			x: next.x - (afterNext.x - current.x) / 6,
			y: next.y - (afterNext.y - current.y) / 6
		};
		path += ` C ${controlOne.x.toFixed(2)} ${controlOne.y.toFixed(2)}, ${controlTwo.x.toFixed(2)} ${controlTwo.y.toFixed(2)}, ${next.x.toFixed(2)} ${next.y.toFixed(2)}`;
	}

	return path;
}

function buildSignal(data: SeriesPoint[]) {
	const samples =
		data.length > 52 ? data.filter((_, index) => index % Math.ceil(data.length / 52) === 0) : data;
	if (samples.length < 2) return null;

	const values = samples.map((point) => point.value).filter(Number.isFinite);
	if (values.length < 2) return null;
	const low = Math.min(...values);
	const high = Math.max(...values);
	const spread = Math.max(high - low, 0.0001);
	const points = samples.map((point, index) => ({
		x: 8 + (index / (samples.length - 1)) * 624,
		y: 18 + ((high - point.value) / spread) * 92
	}));
	const line = smoothPath(points);
	const end = points.at(-1);
	if (!end) return null;
	return {
		line,
		area: `${line} L 632 128 L 8 128 Z`,
		end
	};
}

export function PortfolioSignal({ data }: { data: SeriesPoint[] }) {
	const gradientId = useId().replaceAll(':', '');
	const signal = useMemo(() => buildSignal(data), [data]);

	return (
		<div className="pointer-events-none relative mt-5 h-28 overflow-hidden" aria-hidden="true">
			<div className="text-muted-foreground/80 absolute left-0 top-0 text-[11px] font-medium uppercase">
				Observed return path
			</div>
			{signal ? (
				<svg
					viewBox="0 0 640 136"
					preserveAspectRatio="none"
					className="absolute inset-x-0 bottom-0 h-[6.8rem] w-full overflow-visible"
				>
					<defs>
						<linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
							<stop offset="0%" stopColor="var(--chart-2)" stopOpacity="0.24" />
							<stop offset="100%" stopColor="var(--chart-2)" stopOpacity="0" />
						</linearGradient>
					</defs>
					<path d="M 8 126 H 632" stroke="var(--border)" strokeDasharray="4 8" />
					<path d={signal.area} fill={`url(#${gradientId})`} />
					<path
						className="dashboard-signal-line"
						d={signal.line}
						pathLength="1"
						fill="none"
						stroke="var(--chart-2)"
						strokeWidth="2.5"
						strokeLinecap="round"
					/>
					<circle
						className="dashboard-signal-node"
						cx={signal.end.x}
						cy={signal.end.y}
						r="4"
						fill="var(--chart-2)"
					/>
				</svg>
			) : (
				<div className="border-border/70 absolute inset-x-0 bottom-6 border-t border-dashed" />
			)}
		</div>
	);
}

export function RegimeStateRail({ currentRegime }: { currentRegime?: string | null }) {
	const current = (currentRegime ?? '').toLowerCase();
	const activeIndex = REGIME_STATES.findIndex((state) => {
		const key = state.toLowerCase();
		return current.includes(key) || (key === 'high vol' && current.includes('vol'));
	});

	return (
		<div className="mt-5" aria-label="Market regime state map">
			<div className="relative grid grid-cols-4 gap-1">
				<div className="bg-border absolute left-[12.5%] right-[12.5%] top-2 h-px" aria-hidden />
				{REGIME_STATES.map((state, index) => {
					const active = index === activeIndex;
					return (
						<div key={state} className="relative flex min-w-0 flex-col items-center gap-2">
							<span
								className={cn(
									'bg-card ring-card relative z-10 size-4 rounded-full border-2 ring-4 transition-colors duration-300',
									active ? 'border-primary bg-primary' : 'border-muted-foreground/30'
								)}
							>
								{active ? (
									<span className="bg-primary absolute inset-0 rounded-full opacity-50 motion-safe:animate-ping" />
								) : null}
							</span>
							<span
								className={cn(
									'text-center text-[11px] font-medium',
									active ? 'text-foreground' : 'text-muted-foreground'
								)}
							>
								{state}
							</span>
						</div>
					);
				})}
			</div>
		</div>
	);
}
