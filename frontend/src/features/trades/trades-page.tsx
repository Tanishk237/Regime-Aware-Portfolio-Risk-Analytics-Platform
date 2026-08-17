'use client';

import { Pencil, Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

import { ConfirmDialog } from '@/components/common/confirm-dialog';
import { DataTable, type Column } from '@/components/common/data-table';
import { TradeTypeBadge } from '@/components/domain/finance';
import { RequirePortfolio } from '@/components/layout/require-portfolio';
import { EmptyState, ErrorState, LoadingSkeleton } from '@/components/common/states';
import { PageHeader } from '@/components/layout/top-bar';
import { Button } from '@/components/ui/button';
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { errorMessage } from '@/lib/api';
import { formatCurrency, formatDate, formatNumber, isoDate } from '@/lib/format';
import { useTradeMutations, useTrades } from '@/lib/queries';
import type { Trade, TradeInput } from '@/lib/types';

const emptyTrade = (): TradeInput => ({
	ticker: '',
	transaction_type: 'BUY',
	quantity: 0,
	price: 0,
	transaction_date: isoDate(new Date()),
	broker: '',
	fees: 0,
	taxes: 0,
	currency: 'INR',
	notes: ''
});

export default function TradesRoutePage() {
	return (
		<RequirePortfolio label="trade management">
			{(id) => <TradesPage portfolioId={id} />}
		</RequirePortfolio>
	);
}

function TradesPage({ portfolioId }: { portfolioId: string }) {
	const trades = useTrades(portfolioId);
	const { create, update, remove } = useTradeMutations(portfolioId);
	const [open, setOpen] = useState(false);
	const [editingId, setEditingId] = useState<string | null>(null);
	const [form, setForm] = useState<TradeInput>(emptyTrade());
	const [pendingDelete, setPendingDelete] = useState<Trade | null>(null);

	const submit = async () => {
		if (!form.ticker.trim()) return toast.error('Ticker is required.');
		if (!(form.quantity > 0)) return toast.error('Quantity must be greater than 0.');
		if (!(form.price > 0)) return toast.error('Price must be greater than 0.');
		if ((form.fees ?? 0) < 0 || (form.taxes ?? 0) < 0)
			return toast.error('Fees and taxes cannot be negative.');
		if (!form.transaction_date) return toast.error('Transaction date is required.');

		const payload: TradeInput = { ...form, ticker: form.ticker.trim().toUpperCase() };
		try {
			if (editingId) await update.mutateAsync({ id: editingId, ...payload });
			else await create.mutateAsync(payload);
			toast.success(editingId ? 'Trade updated' : 'Trade added');
			setOpen(false);
			setEditingId(null);
			setForm(emptyTrade());
		} catch (err) {
			toast.error(errorMessage(err));
		}
		return undefined;
	};

	const columns: Array<Column<Trade>> = [
		{ key: 'date', header: 'Date', cell: (row) => formatDate(row.transaction_date) },
		{
			key: 'ticker',
			header: 'Ticker',
			cell: (row) => <span className="font-medium">{row.ticker}</span>
		},
		{ key: 'type', header: 'Type', cell: (row) => <TradeTypeBadge type={row.transaction_type} /> },
		{ key: 'qty', header: 'Qty', align: 'right', cell: (row) => formatNumber(row.quantity, 0) },
		{
			key: 'price',
			header: 'Price',
			align: 'right',
			cell: (row) => formatCurrency(row.price, row.currency ?? 'INR')
		},
		{ key: 'broker', header: 'Broker', cell: (row) => row.broker || '-' },
		{ key: 'fees', header: 'Fees', align: 'right', cell: (row) => formatNumber(row.fees ?? 0) },
		{ key: 'taxes', header: 'Taxes', align: 'right', cell: (row) => formatNumber(row.taxes ?? 0) },
		{ key: 'currency', header: 'Currency', cell: (row) => row.currency ?? 'INR' },
		{
			key: 'notes',
			header: 'Notes',
			cell: (row) => (
				<span className="text-muted-foreground max-w-[14rem] truncate">{row.notes || '-'}</span>
			)
		},
		{
			key: 'actions',
			header: 'Actions',
			align: 'right',
			cell: (row) => (
				<div className="flex justify-end gap-1">
					<Button
						size="icon"
						variant="ghost"
						aria-label="Edit trade"
						onClick={() => {
							setEditingId(row.id);
							setForm({
								ticker: row.ticker,
								transaction_type: row.transaction_type,
								quantity: row.quantity,
								price: row.price,
								transaction_date: row.transaction_date?.slice(0, 10) ?? isoDate(new Date()),
								broker: row.broker ?? '',
								fees: row.fees ?? 0,
								taxes: row.taxes ?? 0,
								currency: row.currency ?? 'INR',
								notes: row.notes ?? ''
							});
							setOpen(true);
						}}
					>
						<Pencil className="size-3.5" />
					</Button>
					<Button
						size="icon"
						variant="ghost"
						aria-label="Delete trade"
						onClick={() => setPendingDelete(row)}
					>
						<Trash2 className="text-negative size-3.5" />
					</Button>
				</div>
			)
		}
	];

	return (
		<div className="space-y-4">
			<PageHeader
				title="Trades"
				description="Manual trade entry keeps positions, P&L, and analytics in sync."
				actions={
					<Button
						size="sm"
						onClick={() => {
							setEditingId(null);
							setForm(emptyTrade());
							setOpen(true);
						}}
					>
						<Plus className="size-4" /> Add trade
					</Button>
				}
			/>

			{trades.isLoading ? (
				<LoadingSkeleton rows={6} />
			) : trades.isError ? (
				<ErrorState error={trades.error} onRetry={() => void trades.refetch()} />
			) : (
				<DataTable
					dense
					columns={columns}
					rows={trades.data ?? []}
					rowKey={(row) => row.id}
					empty={<EmptyState title="Add trades manually or upload a CSV to calculate positions." />}
				/>
			)}

			<Dialog open={open} onOpenChange={setOpen}>
				<DialogContent className="max-h-[90vh] overflow-y-auto">
					<DialogHeader>
						<DialogTitle>{editingId ? 'Edit trade' : 'Add trade'}</DialogTitle>
					</DialogHeader>
					<div className="grid gap-3 sm:grid-cols-2">
						<div className="grid gap-1.5">
							<Label htmlFor="t-ticker">Ticker</Label>
							<Input
								id="t-ticker"
								placeholder="RELIANCE.NS"
								value={form.ticker}
								onChange={(event) => setForm((p) => ({ ...p, ticker: event.target.value }))}
							/>
						</div>
						<div className="grid gap-1.5">
							<Label>Transaction type</Label>
							<Select
								value={form.transaction_type}
								onValueChange={(value) =>
									setForm((p) => ({ ...p, transaction_type: value as 'BUY' | 'SELL' }))
								}
							>
								<SelectTrigger>
									<SelectValue />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="BUY">BUY</SelectItem>
									<SelectItem value="SELL">SELL</SelectItem>
								</SelectContent>
							</Select>
						</div>
						<div className="grid gap-1.5">
							<Label htmlFor="t-qty">Quantity</Label>
							<Input
								id="t-qty"
								type="number"
								min={0}
								value={form.quantity}
								onChange={(event) =>
									setForm((p) => ({ ...p, quantity: Number(event.target.value) }))
								}
							/>
						</div>
						<div className="grid gap-1.5">
							<Label htmlFor="t-price">Price</Label>
							<Input
								id="t-price"
								type="number"
								min={0}
								step="0.01"
								value={form.price}
								onChange={(event) => setForm((p) => ({ ...p, price: Number(event.target.value) }))}
							/>
						</div>
						<div className="grid gap-1.5">
							<Label htmlFor="t-date">Transaction date</Label>
							<Input
								id="t-date"
								type="date"
								value={form.transaction_date}
								onChange={(event) =>
									setForm((p) => ({ ...p, transaction_date: event.target.value }))
								}
							/>
						</div>
						<div className="grid gap-1.5">
							<Label htmlFor="t-broker">Broker</Label>
							<Input
								id="t-broker"
								value={form.broker ?? ''}
								onChange={(event) => setForm((p) => ({ ...p, broker: event.target.value }))}
							/>
						</div>
						<div className="grid gap-1.5">
							<Label htmlFor="t-fees">Fees</Label>
							<Input
								id="t-fees"
								type="number"
								min={0}
								step="0.01"
								value={form.fees ?? 0}
								onChange={(event) => setForm((p) => ({ ...p, fees: Number(event.target.value) }))}
							/>
						</div>
						<div className="grid gap-1.5">
							<Label htmlFor="t-taxes">Taxes</Label>
							<Input
								id="t-taxes"
								type="number"
								min={0}
								step="0.01"
								value={form.taxes ?? 0}
								onChange={(event) => setForm((p) => ({ ...p, taxes: Number(event.target.value) }))}
							/>
						</div>
						<div className="grid gap-1.5">
							<Label htmlFor="t-cur">Currency</Label>
							<Input
								id="t-cur"
								value={form.currency ?? 'INR'}
								onChange={(event) =>
									setForm((p) => ({ ...p, currency: event.target.value.toUpperCase() }))
								}
							/>
						</div>
						<div className="grid gap-1.5 sm:col-span-2">
							<Label htmlFor="t-notes">Notes</Label>
							<Textarea
								id="t-notes"
								value={form.notes ?? ''}
								onChange={(event) => setForm((p) => ({ ...p, notes: event.target.value }))}
							/>
						</div>
					</div>
					<DialogFooter>
						<Button variant="outline" onClick={() => setOpen(false)}>
							Cancel
						</Button>
						<Button onClick={() => void submit()} disabled={create.isPending || update.isPending}>
							{editingId ? 'Save trade' : 'Add trade'}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>

			<ConfirmDialog
				open={Boolean(pendingDelete)}
				onOpenChange={(next) => !next && setPendingDelete(null)}
				title={`Delete trade in ${pendingDelete?.ticker ?? ''}?`}
				description="Positions and P&L will be recalculated by the backend."
				onConfirm={async () => {
					if (!pendingDelete) return;
					try {
						await remove.mutateAsync(pendingDelete.id);
						toast.success('Trade deleted');
					} catch (err) {
						toast.error(errorMessage(err));
					} finally {
						setPendingDelete(null);
					}
				}}
			/>
		</div>
	);
}
