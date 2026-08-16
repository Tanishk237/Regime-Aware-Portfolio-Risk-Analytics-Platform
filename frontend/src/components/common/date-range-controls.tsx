import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

export function DateRangeControls({
	startDate,
	endDate,
	onStartDate,
	onEndDate,
	className
}: {
	startDate: string;
	endDate: string;
	onStartDate: (value: string) => void;
	onEndDate: (value: string) => void;
	className?: string;
}) {
	return (
		<div className={cn('flex flex-wrap items-end gap-3', className)}>
			<div className="grid gap-1.5">
				<Label htmlFor="start-date" className="text-muted-foreground text-xs">
					Start date
				</Label>
				<Input
					id="start-date"
					type="date"
					value={startDate}
					onChange={(event) => onStartDate(event.target.value)}
					className="h-9 w-[9.5rem]"
				/>
			</div>
			<div className="grid gap-1.5">
				<Label htmlFor="end-date" className="text-muted-foreground text-xs">
					End date
				</Label>
				<Input
					id="end-date"
					type="date"
					value={endDate}
					onChange={(event) => onEndDate(event.target.value)}
					className="h-9 w-[9.5rem]"
				/>
			</div>
		</div>
	);
}
