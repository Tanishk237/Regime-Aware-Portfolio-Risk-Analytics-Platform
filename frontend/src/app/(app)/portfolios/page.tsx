'use client';

import { Pencil, Plus, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';
import { toast } from 'sonner';

import { ConfirmDialog } from '@/components/common/confirm-dialog';
import { DataTable, type Column } from '@/components/common/data-table';
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
import { Textarea } from '@/components/ui/textarea';
import { errorMessage } from '@/lib/api';
import { formatDate } from '@/lib/format';
import { usePortfolioMutations, usePortfolios } from '@/lib/queries';
import type { Portfolio } from '@/lib/types';

const EMPTY = { name: '', description: '', base_currency: 'INR', benchmark: 'NIFTY50' };

export default function PortfoliosPage() {
	const { data, isLoading, isError, error, refetch } = usePortfolios();
	const { create, update, remove } = usePortfolioMutations();
	const [form, setForm] = useState<typeof EMPTY & { id?: string }>(EMPTY);
	const [open, setOpen] = useState(false);
	const [pendingDelete, setPendingDelete] = useState<Portfolio | null>(null);

	const submit = async () => {
		if (!form.name.trim()) {
			toast.error('Name is required.');
			return;
		}
		const payload = {
			name: form.name.trim(),
			description: form.description.trim(),
			base_currency: form.base_currency.toUpperCase(),
			benchmark: form.benchmark.toUpperCase()
		};
		try {
			if (form.id) await update.mutateAsync({ id: form.id, ...payload });
			else await create.mutateAsync(payload);
			toast.success(form.id ? 'Portfolio updated' : 'Portfolio created');
			setOpen(false);
			setForm(EMPTY);
		} catch (err) {
			toast.error(errorMessage(err));
		}
	};

	const columns: Array<Column<Portfolio>> = [
		{
			key: 'name',
			header: 'Name',
			cell: (row) => (
				<Link href={`/portfolios/${row.id}`} className="font-medium hover:underline">
					{row.name}
				</Link>
			)
		},
		{
			key: 'description',
			header: 'Description',
			cell: (row) => (
				<span className="text-muted-foreground max-w-[22rem] truncate">
					{row.description || '-'}
				</span>
			)
		},
		{ key: 'currency', header: 'Currency', cell: (row) => row.base_currency ?? 'INR' },
		{ key: 'benchmark', header: 'Benchmark', cell: (row) => row.benchmark ?? '-' },
		{ key: 'created', header: 'Created', cell: (row) => formatDate(row.created_at) },
		{
			key: 'actions',
			header: 'Actions',
			align: 'right',
			cell: (row) => (
				<div className="flex justify-end gap-1">
					<Button asChild size="sm" variant="ghost">
						<Link href={`/portfolios/${row.id}`}>View</Link>
					</Button>
					<Button
						size="icon"
						variant="ghost"
						aria-label="Edit portfolio"
						onClick={() => {
							setForm({
								id: row.id,
								name: row.name,
								description: row.description ?? '',
								base_currency: row.base_currency ?? 'INR',
								benchmark: row.benchmark ?? 'NIFTY50'
							});
							setOpen(true);
						}}
					>
						<Pencil className="size-3.5" />
					</Button>
					<Button
						size="icon"
						variant="ghost"
						aria-label="Delete portfolio"
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
				title="Portfolios"
				description="Create and manage the portfolios feeding your analytics."
				actions={
					<Button
						size="sm"
						onClick={() => {
							setForm(EMPTY);
							setOpen(true);
						}}
					>
						<Plus className="size-4" /> Create Portfolio
					</Button>
				}
			/>

			{isLoading ? (
				<LoadingSkeleton rows={5} />
			) : isError ? (
				<ErrorState error={error} onRetry={() => void refetch()} />
			) : (
				<DataTable
					columns={columns}
					rows={data ?? []}
					rowKey={(row) => row.id}
					empty={
						<EmptyState
							title="Create your first portfolio to begin risk analysis."
							action={
								<Button
									size="sm"
									onClick={() => {
										setForm(EMPTY);
										setOpen(true);
									}}
								>
									<Plus className="size-4" /> Create Portfolio
								</Button>
							}
						/>
					}
				/>
			)}

			<Dialog open={open} onOpenChange={setOpen}>
				<DialogContent>
					<DialogHeader>
						<DialogTitle>{form.id ? 'Edit portfolio' : 'Create portfolio'}</DialogTitle>
					</DialogHeader>
					<div className="grid gap-3">
						<div className="grid gap-1.5">
							<Label htmlFor="p-name">Name</Label>
							<Input
								id="p-name"
								value={form.name}
								onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
							/>
						</div>
						<div className="grid gap-1.5">
							<Label htmlFor="p-desc">Description</Label>
							<Textarea
								id="p-desc"
								value={form.description}
								onChange={(event) =>
									setForm((prev) => ({ ...prev, description: event.target.value }))
								}
							/>
						</div>
						<div className="grid gap-3 sm:grid-cols-2">
							<div className="grid gap-1.5">
								<Label htmlFor="p-cur">Base currency</Label>
								<Input
									id="p-cur"
									value={form.base_currency}
									onChange={(event) =>
										setForm((prev) => ({
											...prev,
											base_currency: event.target.value.toUpperCase()
										}))
									}
								/>
							</div>
							<div className="grid gap-1.5">
								<Label htmlFor="p-bench">Benchmark</Label>
								<Input
									id="p-bench"
									value={form.benchmark}
									onChange={(event) =>
										setForm((prev) => ({ ...prev, benchmark: event.target.value.toUpperCase() }))
									}
								/>
							</div>
						</div>
					</div>
					<DialogFooter>
						<Button variant="outline" onClick={() => setOpen(false)}>
							Cancel
						</Button>
						<Button onClick={() => void submit()} disabled={create.isPending || update.isPending}>
							{form.id ? 'Save changes' : 'Create portfolio'}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>

			<ConfirmDialog
				open={Boolean(pendingDelete)}
				onOpenChange={(next) => !next && setPendingDelete(null)}
				title={`Delete ${pendingDelete?.name ?? 'portfolio'}?`}
				description="This removes the portfolio and its trades from the backend. This cannot be undone."
				onConfirm={async () => {
					if (!pendingDelete) return;
					try {
						await remove.mutateAsync(pendingDelete.id);
						toast.success('Portfolio deleted');
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
