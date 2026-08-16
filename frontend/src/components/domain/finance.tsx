import { Badge } from '@/components/ui/badge';
import { formatCurrency, formatPercent, signClass } from '@/lib/format';
import { cn } from '@/lib/utils';

export function PnLValue({
	value,
	currency = 'INR',
	percent,
	className
}: {
	value?: number | null;
	currency?: string;
	percent?: boolean;
	className?: string;
}) {
	const text = percent ? formatPercent(value) : formatCurrency(value, currency);
	const prefix = value && value > 0 ? '+' : '';
	return (
		<span className={cn('num tabular-nums', signClass(value), className)}>
			{value === null || value === undefined ? '—' : `${prefix}${text}`}
		</span>
	);
}

const REGIME_STYLES: Record<string, string> = {
	bull: 'bg-positive-muted text-positive border-positive/30',
	bear: 'bg-negative-muted text-negative border-negative/30',
	'high volatility': 'bg-warning-muted text-warning-foreground border-warning/40',
	highvolatility: 'bg-warning-muted text-warning-foreground border-warning/40',
	crisis: 'bg-crisis text-crisis-foreground border-crisis'
};

export function regimeKey(label?: string | null) {
	return (label ?? 'unknown').toString().trim().toLowerCase().replace(/_/g, ' ');
}

export function RegimeBadge({
	label,
	className,
	size = 'sm'
}: {
	label?: string | null;
	className?: string;
	size?: 'sm' | 'lg';
}) {
	const key = regimeKey(label);
	const style = REGIME_STYLES[key] ?? 'bg-muted text-muted-foreground border-border';
	return (
		<Badge
			variant="outline"
			className={cn(
				'capitalize',
				style,
				size === 'lg' ? 'px-3 py-1 text-sm' : 'text-xs',
				className
			)}
		>
			{label ? key : 'Unknown'}
		</Badge>
	);
}

export type Severity = 'high' | 'medium' | 'low';

const SEVERITY_STYLES: Record<Severity, string> = {
	high: 'bg-negative-muted text-negative border-negative/30',
	medium: 'bg-warning-muted text-warning-foreground border-warning/40',
	low: 'bg-info-muted text-info border-info/30'
};

export function SeverityBadge({ severity, className }: { severity: Severity; className?: string }) {
	return (
		<Badge
			variant="outline"
			className={cn('text-xs uppercase', SEVERITY_STYLES[severity], className)}
		>
			{severity}
		</Badge>
	);
}

export function CategoryBadge({ category, className }: { category: string; className?: string }) {
	return (
		<Badge variant="secondary" className={cn('text-xs font-normal', className)}>
			{category}
		</Badge>
	);
}

export function TradeTypeBadge({ type }: { type: string }) {
	const isBuy = type?.toUpperCase() === 'BUY';
	return (
		<Badge
			variant="outline"
			className={cn(
				'text-xs font-semibold',
				isBuy
					? 'bg-positive-muted text-positive border-positive/30'
					: 'bg-negative-muted text-negative border-negative/30'
			)}
		>
			{type?.toUpperCase() || '—'}
		</Badge>
	);
}
