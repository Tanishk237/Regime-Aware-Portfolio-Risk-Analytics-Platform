'use client';

import { useState } from 'react';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

import { Button } from '@/components/ui/button';
import { formatCurrency, formatPercent } from '@/lib/format';
import type { SectorAllocation } from '@/lib/types';
import { cn } from '@/lib/utils';

const colors = [
	'var(--chart-1)',
	'var(--chart-2)',
	'var(--chart-3)',
	'var(--chart-5)',
	'var(--positive)',
	'var(--info)',
	'var(--chart-4)',
	'var(--warning)',
	'var(--negative)'
];

type SectorTooltipProps = {
	active?: boolean;
	payload?: Array<{ payload?: SectorAllocation }>;
	currency: string;
};

function SectorTooltip({ active, payload, currency }: SectorTooltipProps) {
	const item = payload?.[0]?.payload;
	if (!active || !item) return null;
	return (
		<div className="bg-popover text-popover-foreground min-w-44 rounded-md border px-3 py-2 text-xs">
			<p className="font-medium">{item.sector}</p>
			<p className="text-muted-foreground mt-1">
				{formatCurrency(item.market_value, currency)} · {formatPercent(item.weight)}
			</p>
			<p className="text-muted-foreground mt-0.5">
				{item.holdings_count} {item.holdings_count === 1 ? 'holding' : 'holdings'}
			</p>
		</div>
	);
}

export function SectorAllocationChart({
	data,
	currency
}: {
	data: SectorAllocation[];
	currency: string;
}) {
	const [activeSector, setActiveSector] = useState(data[0]?.sector ?? '');
	const selected = data.find((item) => item.sector === activeSector) ?? data[0];

	return (
		<div className="grid items-center gap-4 sm:grid-cols-[minmax(13rem,0.9fr)_minmax(0,1.1fr)]">
			<div className="relative mx-auto h-56 w-full max-w-64" aria-label="Sector allocation chart">
				<ResponsiveContainer width="100%" height="100%">
					<PieChart>
						<Pie
							data={data}
							dataKey="market_value"
							nameKey="sector"
							innerRadius={67}
							outerRadius={91}
							paddingAngle={2}
							cornerRadius={4}
							stroke="var(--card)"
							strokeWidth={2}
							animationDuration={520}
						>
							{data.map((item, index) => (
								<Cell
									key={item.sector}
									fill={colors[index % colors.length]}
									opacity={!selected || selected.sector === item.sector ? 1 : 0.42}
								/>
							))}
						</Pie>
						<Tooltip content={<SectorTooltip currency={currency} />} />
					</PieChart>
				</ResponsiveContainer>
				{selected ? (
					<div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center px-16 text-center">
						<span className="num text-xl font-semibold">{formatPercent(selected.weight)}</span>
						<span className="text-muted-foreground mt-1 line-clamp-2 text-xs">
							{selected.sector}
						</span>
					</div>
				) : null}
			</div>

			<div className="space-y-1" aria-label="Sector allocation legend">
				{data.map((item, index) => {
					const active = selected?.sector === item.sector;
					return (
						<Button
							key={item.sector}
							type="button"
							variant="ghost"
							aria-pressed={active}
							onClick={() => setActiveSector(item.sector)}
							className={cn(
								'h-auto w-full justify-start gap-3 px-2.5 py-2 text-left transition-colors duration-200',
								active && 'bg-muted'
							)}
						>
							<span
								className="size-2.5 shrink-0 rounded-full"
								style={{ backgroundColor: colors[index % colors.length] }}
							/>
							<span className="min-w-0 flex-1">
								<span className="block truncate text-sm font-medium">{item.sector}</span>
								<span className="text-muted-foreground block truncate text-xs">
									{item.tickers.join(', ')}
								</span>
							</span>
							<span className="num shrink-0 text-sm font-medium">{formatPercent(item.weight)}</span>
						</Button>
					);
				})}
			</div>
		</div>
	);
}
