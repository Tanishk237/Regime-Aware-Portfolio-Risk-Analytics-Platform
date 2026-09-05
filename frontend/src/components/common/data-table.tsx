import type { ReactNode } from 'react';

import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow
} from '@/components/ui/table';
import { cn } from '@/lib/utils';

export type Column<T> = {
	key: string;
	header: ReactNode;
	align?: 'left' | 'right' | 'center';
	className?: string;
	cell: (row: T, index: number) => ReactNode;
};

export function DataTable<T>({
	columns,
	rows,
	rowKey,
	empty,
	dense,
	className
}: {
	columns: Array<Column<T>>;
	rows: T[];
	rowKey: (row: T, index: number) => string;
	empty?: ReactNode;
	dense?: boolean;
	className?: string;
}) {
	if (rows.length === 0 && empty) return <>{empty}</>;

	return (
		<div
			className={cn(
				'panel-surface border-border/70 shadow-soft overflow-x-auto rounded-xl border',
				className
			)}
		>
			<Table>
				<TableHeader className="bg-surface-strong/55">
					<TableRow className="hover:bg-transparent">
						{columns.map((column) => (
							<TableHead
								key={column.key}
								className={cn(
									'text-muted-foreground h-10 whitespace-nowrap text-xs font-semibold uppercase tracking-wide',
									column.align === 'right' && 'text-right',
									column.align === 'center' && 'text-center',
									column.className
								)}
							>
								{column.header}
							</TableHead>
						))}
					</TableRow>
				</TableHeader>
				<TableBody>
					{rows.map((row, index) => (
						<TableRow
							key={rowKey(row, index)}
							className="border-border/60 hover:bg-surface-strong/45 transition-colors"
						>
							{columns.map((column) => (
								<TableCell
									key={column.key}
									className={cn(
										'whitespace-nowrap text-sm',
										dense ? 'py-2' : 'py-3',
										column.align === 'right' && 'text-right',
										column.align === 'center' && 'text-center',
										column.className
									)}
								>
									{column.cell(row, index)}
								</TableCell>
							))}
						</TableRow>
					))}
				</TableBody>
			</Table>
		</div>
	);
}
