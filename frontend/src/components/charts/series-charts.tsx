import { useId } from 'react';
import {
	Area,
	AreaChart,
	Bar,
	BarChart,
	Cell,
	CartesianGrid,
	Line,
	LineChart,
	ReferenceLine,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis
} from 'recharts';

import { shortDate } from '@/lib/format';

type Point = { date: string; value: number };

const percentAxis = new Intl.NumberFormat('en', {
	style: 'percent',
	maximumFractionDigits: 2
});

const axisProps = {
	tick: { fontSize: 12, fill: 'var(--muted-foreground)' },
	stroke: 'var(--border)'
} as const;

function TooltipBox({
	active,
	payload,
	label,
	digits = 4,
	percent,
	stateLabels
}: {
	active?: boolean;
	payload?: Array<{ value?: number | string }>;
	label?: string | number;
	digits?: number;
	percent?: boolean;
	stateLabels?: Record<string, string>;
}) {
	if (!active || !payload?.length) return null;
	const raw = Number(payload[0]?.value ?? 0);
	return (
		<div className="bg-popover text-popover-foreground rounded-md border px-2.5 py-1.5 text-xs shadow-sm">
			<p className="text-muted-foreground">{String(label)}</p>
			<p className="num font-semibold">
				{stateLabels?.[String(raw)] ??
					(percent ? `${(raw * 100).toFixed(2)}%` : raw.toFixed(digits))}
			</p>
		</div>
	);
}

export function SeriesLineChart({
	data,
	percent = true,
	color = 'var(--chart-1)',
	height = 240,
	gradient = true,
	stateLabels
}: {
	data: Point[];
	percent?: boolean;
	color?: string;
	height?: number;
	gradient?: boolean;
	stateLabels?: Record<string, string>;
}) {
	const id = useId().replaceAll(':', '');
	if (gradient && !stateLabels) {
		const fillId = `series-fill-${id}`;
		const strokeId = `series-stroke-${id}`;
		return (
			<ResponsiveContainer width="100%" height={height}>
				<AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
					<defs>
						<linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
							<stop offset="0%" stopColor={color} stopOpacity={0.28} />
							<stop offset="100%" stopColor={color} stopOpacity={0.02} />
						</linearGradient>
						<linearGradient id={strokeId} x1="0" y1="0" x2="1" y2="0">
							<stop offset="0%" stopColor={color} />
							<stop
								offset="100%"
								stopColor={color === 'var(--chart-1)' ? 'var(--chart-2)' : color}
								stopOpacity={0.85}
							/>
						</linearGradient>
					</defs>
					<CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
					<XAxis dataKey="date" tickFormatter={shortDate} minTickGap={28} {...axisProps} />
					<YAxis
						tickFormatter={(value: number) =>
							percent ? percentAxis.format(value) : value.toFixed(2)
						}
						{...axisProps}
					/>
					<Tooltip content={<TooltipBox percent={percent} />} />
					<ReferenceLine y={0} stroke="var(--border)" />
					<Area
						type="monotone"
						dataKey="value"
						stroke={`url(#${strokeId})`}
						strokeWidth={2}
						fill={`url(#${fillId})`}
						dot={false}
						activeDot={{ r: 3, fill: color, strokeWidth: 0 }}
					/>
				</AreaChart>
			</ResponsiveContainer>
		);
	}

	return (
		<ResponsiveContainer width="100%" height={height}>
			<LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
				<CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
				<XAxis dataKey="date" tickFormatter={shortDate} minTickGap={28} {...axisProps} />
				<YAxis
					width={stateLabels ? 100 : 60}
					ticks={stateLabels ? Object.keys(stateLabels).map(Number) : undefined}
					domain={stateLabels ? [0, Object.keys(stateLabels).length - 1] : undefined}
					tickFormatter={(value: number) =>
						stateLabels?.[String(value)] ?? (percent ? percentAxis.format(value) : value.toFixed(2))
					}
					{...axisProps}
				/>
				<Tooltip content={<TooltipBox percent={percent} stateLabels={stateLabels} />} />
				<Line
					type={stateLabels ? 'stepAfter' : 'monotone'}
					dataKey="value"
					stroke={color}
					strokeWidth={2}
					dot={false}
				/>
			</LineChart>
		</ResponsiveContainer>
	);
}

export function SeriesAreaChart({
	data,
	color = 'var(--chart-4)',
	height = 220,
	percent = true
}: {
	data: Point[];
	color?: string;
	height?: number;
	percent?: boolean;
}) {
	const fillId = `area-fill-${useId().replaceAll(':', '')}`;
	return (
		<ResponsiveContainer width="100%" height={height}>
			<AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
				<defs>
					<linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
						<stop offset="0%" stopColor={color} stopOpacity={0.05} />
						<stop offset="100%" stopColor={color} stopOpacity={0.35} />
					</linearGradient>
				</defs>
				<CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
				<XAxis dataKey="date" tickFormatter={shortDate} minTickGap={28} {...axisProps} />
				<YAxis
					tickFormatter={(value: number) =>
						percent ? percentAxis.format(value) : value.toFixed(2)
					}
					{...axisProps}
				/>
				<Tooltip content={<TooltipBox percent={percent} />} />
				<ReferenceLine y={0} stroke="var(--border)" />
				<Area
					type="monotone"
					dataKey="value"
					stroke={color}
					strokeWidth={1.5}
					fill={`url(#${fillId})`}
				/>
			</AreaChart>
		</ResponsiveContainer>
	);
}

export function SeriesBarChart({ data, height = 220 }: { data: Point[]; height?: number }) {
	const id = useId().replaceAll(':', '');
	return (
		<ResponsiveContainer width="100%" height={height}>
			<BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
				<defs>
					<linearGradient id={`bar-gain-${id}`} x1="0" y1="0" x2="0" y2="1">
						<stop offset="0%" stopColor="var(--chart-2)" stopOpacity={0.95} />
						<stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0.3} />
					</linearGradient>
					<linearGradient id={`bar-loss-${id}`} x1="0" y1="0" x2="0" y2="1">
						<stop offset="0%" stopColor="var(--chart-4)" stopOpacity={0.3} />
						<stop offset="100%" stopColor="var(--chart-4)" stopOpacity={0.9} />
					</linearGradient>
				</defs>
				<CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
				<XAxis dataKey="date" tickFormatter={shortDate} minTickGap={28} {...axisProps} />
				<YAxis tickFormatter={(value: number) => percentAxis.format(value)} {...axisProps} />
				<Tooltip content={<TooltipBox percent />} />
				<ReferenceLine y={0} stroke="var(--border)" />
				<Bar dataKey="value" radius={[1, 1, 0, 0]}>
					{data.map((point) => (
						<Cell key={point.date} fill={`url(#bar-${point.value < 0 ? 'loss' : 'gain'}-${id})`} />
					))}
				</Bar>
			</BarChart>
		</ResponsiveContainer>
	);
}
