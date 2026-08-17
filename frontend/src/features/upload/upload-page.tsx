'use client';

import { CheckCircle2, FileSpreadsheet, Upload as UploadIcon, X } from 'lucide-react';
import { useRef, useState } from 'react';
import { toast } from 'sonner';

import { SectionCard } from '@/components/charts/chart-card';
import { PageHeader } from '@/components/layout/top-bar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { errorMessage } from '@/lib/api';
import { useCsvUpload } from '@/lib/queries';
import { cn } from '@/lib/utils';

const REQUIRED_COLUMNS = ['ticker', 'transaction_type', 'quantity', 'price', 'transaction_date'];
const OPTIONAL_COLUMNS = ['broker', 'fees', 'taxes', 'currency', 'notes'];

type Parsed = { headers: string[]; rows: string[][]; missing: string[] };

function parseCsv(text: string): Parsed {
	const lines = text
		.replace(/\r\n/g, '\n')
		.split('\n')
		.filter((line) => line.trim() !== '');
	const split = (line: string) => line.split(',').map((cell) => cell.trim().replace(/^"|"$/g, ''));
	const headers = lines.length ? split(lines[0] ?? '').map((h) => h.toLowerCase()) : [];
	const rows = lines.slice(1, 11).map(split);
	const missing = REQUIRED_COLUMNS.filter((column) => !headers.includes(column));
	return { headers, rows, missing };
}

export default function UploadPage() {
	const upload = useCsvUpload();
	const inputRef = useRef<HTMLInputElement>(null);
	const [file, setFile] = useState<File | null>(null);
	const [parsed, setParsed] = useState<Parsed | null>(null);
	const [dragging, setDragging] = useState(false);
	const [name, setName] = useState('');
	const [description, setDescription] = useState('');
	const [baseCurrency, setBaseCurrency] = useState('INR');
	const [benchmark, setBenchmark] = useState('NIFTY50');
	const [result, setResult] = useState<Record<string, unknown> | null>(null);

	const accept = async (next: File) => {
		if (!next.name.toLowerCase().endsWith('.csv')) {
			toast.error('Please select a .csv file');
			return;
		}
		setFile(next);
		setResult(null);
		setParsed(parseCsv(await next.text()));
		if (!name.trim()) setName(next.name.replace(/\.csv$/i, '').replace(/[-_]/g, ' '));
	};

	const submit = async () => {
		if (!file) return;
		if (!name.trim()) {
			toast.error('Portfolio name is required.');
			return;
		}
		const formData = new FormData();
		formData.append('name', name.trim());
		formData.append('description', description.trim());
		formData.append('base_currency', baseCurrency.trim().toUpperCase() || 'INR');
		formData.append('benchmark', benchmark.trim().toUpperCase() || 'NIFTY50');
		formData.append('file', file);
		try {
			const data = await upload.mutateAsync(formData);
			setResult(data);
			toast.success('CSV uploaded and portfolio created');
		} catch (error) {
			toast.error(errorMessage(error));
		}
	};

	const invalid = Boolean(parsed && parsed.missing.length > 0);

	return (
		<div className="space-y-4">
			<PageHeader
				title="CSV Upload"
				description="Create a new portfolio by importing a backend-compatible trade CSV."
			/>

			<SectionCard title="New portfolio details">
				<div className="grid gap-3 lg:grid-cols-2">
					<div className="grid gap-1.5">
						<Label htmlFor="portfolio-name">Portfolio name</Label>
						<Input
							id="portfolio-name"
							value={name}
							onChange={(event) => setName(event.target.value)}
							placeholder="Long-term India equity"
						/>
					</div>
					<div className="grid gap-1.5">
						<Label htmlFor="benchmark">Benchmark</Label>
						<Input
							id="benchmark"
							value={benchmark}
							onChange={(event) => setBenchmark(event.target.value.toUpperCase())}
						/>
					</div>
					<div className="grid gap-1.5">
						<Label htmlFor="currency">Base currency</Label>
						<Input
							id="currency"
							value={baseCurrency}
							onChange={(event) => setBaseCurrency(event.target.value.toUpperCase())}
						/>
					</div>
					<div className="grid gap-1.5 lg:row-span-2">
						<Label htmlFor="description">Description</Label>
						<Textarea
							id="description"
							value={description}
							onChange={(event) => setDescription(event.target.value)}
						/>
					</div>
				</div>
			</SectionCard>

			<SectionCard title="Upload trade CSV">
				<div
					role="button"
					tabIndex={0}
					onClick={() => inputRef.current?.click()}
					onKeyDown={(event) => {
						if (event.key === 'Enter' || event.key === ' ') inputRef.current?.click();
					}}
					onDragOver={(event) => {
						event.preventDefault();
						setDragging(true);
					}}
					onDragLeave={() => setDragging(false)}
					onDrop={(event) => {
						event.preventDefault();
						setDragging(false);
						const dropped = event.dataTransfer.files?.[0];
						if (dropped) void accept(dropped);
					}}
					className={cn(
						'flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-6 py-10 text-center transition-colors',
						dragging ? 'border-primary bg-primary/5' : 'hover:bg-surface-strong/50'
					)}
				>
					<span className="bg-surface-strong text-muted-foreground rounded-full p-3">
						<UploadIcon className="size-5" />
					</span>
					<p className="text-sm font-medium">Drag and drop your CSV here</p>
					<p className="text-muted-foreground text-xs">or click to browse</p>
					<input
						ref={inputRef}
						type="file"
						accept=".csv,text/csv"
						className="hidden"
						onChange={(event) => {
							const next = event.target.files?.[0];
							if (next) void accept(next);
						}}
					/>
				</div>

				<div className="mt-4 flex flex-wrap items-center gap-2">
					<Button onClick={() => void submit()} disabled={!file || invalid || upload.isPending}>
						{upload.isPending ? 'Uploading...' : 'Upload CSV'}
					</Button>
					{file ? (
						<Button
							variant="ghost"
							onClick={() => {
								setFile(null);
								setParsed(null);
								setResult(null);
							}}
						>
							<X className="size-4" /> Clear
						</Button>
					) : null}
				</div>
			</SectionCard>

			<SectionCard title="Expected format">
				<div className="flex flex-wrap gap-1.5 text-xs">
					{REQUIRED_COLUMNS.map((column) => (
						<span key={column} className="num bg-primary/10 text-primary rounded-md px-2 py-1">
							{column} *
						</span>
					))}
					{OPTIONAL_COLUMNS.map((column) => (
						<span
							key={column}
							className="num bg-surface-strong text-muted-foreground rounded-md px-2 py-1"
						>
							{column}
						</span>
					))}
				</div>
			</SectionCard>

			{parsed ? (
				<SectionCard
					title={file?.name ?? 'Preview'}
					description={`${parsed.headers.length} columns detected · showing first ${parsed.rows.length} rows`}
					action={
						invalid ? (
							<span className="text-negative inline-flex items-center gap-1 text-xs font-medium">
								<X className="size-3.5" /> Missing: {parsed.missing.join(', ')}
							</span>
						) : (
							<span className="text-positive inline-flex items-center gap-1 text-xs font-medium">
								<CheckCircle2 className="size-3.5" /> All required columns present
							</span>
						)
					}
				>
					<div className="overflow-x-auto rounded-lg border">
						<table className="w-full text-xs">
							<thead className="bg-surface-strong/60">
								<tr>
									{parsed.headers.map((header) => (
										<th key={header} className="px-3 py-2 text-left font-semibold uppercase">
											{header}
										</th>
									))}
								</tr>
							</thead>
							<tbody>
								{parsed.rows.map((row, index) => (
									<tr key={index} className="border-t">
										{row.map((cell, cellIndex) => (
											<td key={cellIndex} className="num whitespace-nowrap px-3 py-1.5">
												{cell}
											</td>
										))}
									</tr>
								))}
							</tbody>
						</table>
					</div>
				</SectionCard>
			) : null}

			{result ? (
				<SectionCard title="Upload result">
					<pre className="num bg-surface-strong overflow-x-auto rounded-md p-3 text-xs">
						{JSON.stringify(result, null, 2)}
					</pre>
				</SectionCard>
			) : null}

			{!file ? (
				<p className="text-muted-foreground flex items-center gap-1.5 text-xs">
					<FileSpreadsheet className="size-3.5" /> Required dates should use YYYY-MM-DD and
					transaction_type should be BUY or SELL.
				</p>
			) : null}
		</div>
	);
}
