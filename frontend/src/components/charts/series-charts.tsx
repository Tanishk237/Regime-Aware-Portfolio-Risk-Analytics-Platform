import {
	Area,
	AreaChart,
	Bar,
	BarChart,
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

const axisProps = {
	tick: { fontSize: 11, fill: 'var(--muted-foreground)' },
	stroke: 'var(--border)'
} as const;

function TooltipBox({
	active,
	payload,
	label,
	digits = 4,
	percent
}: {
	active?: boolean;
	payload?: Array<{ value?: number | string }>;
	label?: string | number;
	digits?: number;
	percent?: boolean;
}) {
	if (!active || !payload?.length) return null;
	const raw = Number(payload[0]?.value ?? 0);
	return (
		<div className="bg-popover text-popover-foreground rounded-md border px-2.5 py-1.5 text-xs shadow-sm">
			<p className="text-muted-foreground">{String(label)}</p>
			<p className="num font-semibold">
				{percent ? `${(raw * 100).toFixed(2)}%` : raw.toFixed(digits)}
			</p>
		</div>
	);
}

export function SeriesLineChart({
	data,
	percent = true,
	color = 'var(--chart-1)',
	height = 240
}: {
	data: Point[];
	percent?: boolean;
	color?: string;
	height?: number;
}) {
	return (
		<ResponsiveContainer width="100%" height={height}>
			<LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
				<CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
				<XAxis dataKey="date" tickFormatter={shortDate} minTickGap={28} {...axisProps} />
				<YAxis
					tickFormatter={(value: number) =>
						percent ? `${(value * 100).toFixed(0)}%` : value.toFixed(2)
					}
					{...axisProps}
				/>
				<Tooltip content={<TooltipBox percent={percent} />} />
				<Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} />
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
	return (
		<ResponsiveContainer width="100%" height={height}>
			<AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
				<defs>
					<linearGradient id="ddFill" x1="0" y1="0" x2="0" y2="1">
						<stop offset="0%" stopColor={color} stopOpacity={0.05} />
						<stop offset="100%" stopColor={color} stopOpacity={0.35} />
					</linearGradient>
				</defs>
				<CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
				<XAxis dataKey="date" tickFormatter={shortDate} minTickGap={28} {...axisProps} />
				<YAxis
					tickFormatter={(value: number) =>
						percent ? `${(value * 100).toFixed(0)}%` : value.toFixed(2)
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
					fill="url(#ddFill)"
				/>
			</AreaChart>
		</ResponsiveContainer>
	);
}

export function SeriesBarChart({ data, height = 220 }: { data: Point[]; height?: number }) {
	return (
		<ResponsiveContainer width="100%" height={height}>
			<BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
				<CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
				<XAxis dataKey="date" tickFormatter={shortDate} minTickGap={28} {...axisProps} />
				<YAxis tickFormatter={(value: number) => `${(value * 100).toFixed(1)}%`} {...axisProps} />
				<Tooltip content={<TooltipBox percent />} />
				<ReferenceLine y={0} stroke="var(--border)" />
				<Bar dataKey="value" radius={[1, 1, 0, 0]} fill="var(--chart-1)" />
			</BarChart>
		</ResponsiveContainer>
	);
}
