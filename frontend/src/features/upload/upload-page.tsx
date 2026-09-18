'use client';

import {
	ArrowRight,
	CheckCircle2,
	FileCheck2,
	FileSpreadsheet,
	Loader2,
	Sparkles,
	Upload as UploadIcon,
	X
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import { toast } from 'sonner';

import { SectionCard } from '@/components/charts/chart-card';
import { WarningState } from '@/components/common/states';
import { PageHeader } from '@/components/layout/top-bar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Textarea } from '@/components/ui/textarea';
import { errorMessage } from '@/lib/api';
import { fetchPortfolioIntelligence } from '@/lib/api/intelligence';
import type { CsvUploadResult } from '@/lib/api/portfolio';
import { useAuth } from '@/lib/auth';
import { useSelectedPortfolio } from '@/lib/portfolio-context';
import { useCsvPreview, useCsvResolve, useCsvUpload, useDemoPortfolio } from '@/lib/queries';
import type { CsvPreview, CsvResolution, PortfolioIntelligence } from '@/lib/types';
import { cn } from '@/lib/utils';

const REQUIRED_COLUMNS = ['ticker', 'transaction_type', 'quantity', 'price', 'transaction_date'];
const OPTIONAL_COLUMNS = ['broker', 'fees', 'taxes', 'currency', 'notes'];
const MAX_FILE_SIZE = 5 * 1024 * 1024;

function fileSize(bytes: number) {
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
	return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UploadPage() {
	const router = useRouter();
	const queryClient = useQueryClient();
	const { user } = useAuth();
	const { select } = useSelectedPortfolio();
	const upload = useCsvUpload();
	const preview = useCsvPreview();
	const resolveCsv = useCsvResolve();
	const demoPortfolio = useDemoPortfolio();
	const inputRef = useRef<HTMLInputElement>(null);
	const [file, setFile] = useState<File | null>(null);
	const [parsed, setParsed] = useState<CsvPreview | null>(null);
	const [resolution, setResolution] = useState<CsvResolution | null>(null);
	const [dragging, setDragging] = useState(false);
	const [name, setName] = useState('');
	const [description, setDescription] = useState('');
	const [baseCurrency, setBaseCurrency] = useState('INR');
	const [benchmark, setBenchmark] = useState('NIFTY50');
	const [result, setResult] = useState<CsvUploadResult | null>(null);
	const [intelligence, setIntelligence] = useState<PortfolioIntelligence | null>(null);
	const [intelligenceLoading, setIntelligenceLoading] = useState(false);

	const invalid = Boolean(parsed && !parsed.valid);
	const activeStep = result ? 3 : file ? 2 : 1;

	const clearFile = () => {
		setFile(null);
		setParsed(null);
		setResolution(null);
		setResult(null);
		setIntelligence(null);
		if (inputRef.current) inputRef.current.value = '';
	};

	const accept = async (next: File) => {
		if (!next.name.toLowerCase().endsWith('.csv')) {
			toast.error('Please select a .csv file.');
			return;
		}
		if (next.size > MAX_FILE_SIZE) {
			toast.error('CSV files must be smaller than 5 MB.');
			return;
		}

		setFile(next);
		setResult(null);
		setIntelligence(null);
		setParsed(null);
		setResolution(null);
		if (!name.trim()) setName(next.name.replace(/\.csv$/i, '').replace(/[-_]/g, ' '));
		try {
			const nextParsed = await preview.mutateAsync(next);
			setParsed(nextParsed);
			if (nextParsed.valid) toast.success(`${next.name} is validated and ready to import.`);
			else
				toast.error(
					`Review ${nextParsed.errors.length} CSV validation issue${nextParsed.errors.length === 1 ? '' : 's'}.`
				);
		} catch (error) {
			setFile(null);
			toast.error(errorMessage(error));
		}
	};

	const resolveIssues = async () => {
		if (!file) return;
		try {
			const repaired = await resolveCsv.mutateAsync(file);
			setResolution(repaired);
			setParsed(repaired.report);
			if (repaired.changes.length) {
				const repairedFile = new File([repaired.resolved_csv], file.name, { type: 'text/csv' });
				setFile(repairedFile);
				if (inputRef.current) inputRef.current.value = '';
			}

			if (repaired.report.valid) {
				toast.success(
					repaired.changes.length
						? `Resolved ${repaired.changes.length} CSV issue${repaired.changes.length === 1 ? '' : 's'}.`
						: 'The CSV is valid and ready to import.'
				);
			} else if (repaired.changes.length) {
				toast.warning('Safe fixes were applied. Some rows still need your review.');
			} else {
				toast.error('These issues need manual review; no safe automatic fix was found.');
			}
		} catch (error) {
			toast.error(errorMessage(error));
		}
	};

	const submit = async () => {
		if (!file || !parsed?.valid) return;
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
			select(data.portfolio.id);
			setResult(data);
			toast.success(`${data.portfolio.name} was created successfully.`);
			setIntelligenceLoading(true);
			void fetchPortfolioIntelligence(queryClient, data.portfolio.id)
				.then(setIntelligence)
				.catch(() => undefined)
				.finally(() => setIntelligenceLoading(false));
		} catch (error) {
			toast.error(errorMessage(error));
		}
	};

	const createDemo = async () => {
		try {
			const data = await demoPortfolio.create.mutateAsync();
			select(data.portfolio.id);
			toast.success('Demo portfolio is ready.');
			router.push('/dashboard');
		} catch (error) {
			toast.error(errorMessage(error));
		}
	};

	return (
		<div className="space-y-5">
			<PageHeader
				title="Import portfolio"
				description={
					user?.isGuest
						? 'Upload a trade CSV to create an isolated portfolio in this temporary workspace.'
						: 'Create a portfolio from your trade history, validate it, and continue directly to analytics.'
				}
				actions={
					user?.isGuest ? (
						<Button
							size="sm"
							variant="outline"
							onClick={() => void createDemo()}
							disabled={demoPortfolio.create.isPending}
						>
							{demoPortfolio.create.isPending ? 'Preparing demo...' : 'Try Demo Portfolio'}
						</Button>
					) : undefined
				}
			/>

			{user?.isGuest ? (
				<WarningState
					title="Guest workspace"
					description="Your portfolio is isolated to this browser tab. Create an account to keep portfolios and analytics after you leave."
				/>
			) : null}

			<div aria-label="CSV import progress" className="grid grid-cols-3 gap-2">
				{['Select file', 'Review data', 'Portfolio ready'].map((label, index) => {
					const step = index + 1;
					const complete = activeStep > step;
					const active = activeStep === step;
					return (
						<div
							key={label}
							className={cn(
								'border-border/70 flex min-w-0 items-center gap-2 border-b-2 px-1 pb-2 text-xs transition-colors duration-300 sm:text-sm',
								active || complete ? 'border-primary text-foreground' : 'text-muted-foreground'
							)}
						>
							<span
								className={cn(
									'flex size-5 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold transition-colors duration-300',
									complete && 'border-positive bg-positive text-positive-foreground',
									active && 'border-primary bg-primary text-primary-foreground'
								)}
							>
								{complete ? <CheckCircle2 className="size-3" /> : step}
							</span>
							<span className="truncate">{label}</span>
						</div>
					);
				})}
			</div>

			<SectionCard
				title="Portfolio details"
				description="These details identify the imported portfolio across Latent."
			>
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
							placeholder="Optional portfolio context"
						/>
					</div>
				</div>
			</SectionCard>

			<SectionCard
				title="Trade CSV"
				description="Maximum file size 5 MB. Dates should use YYYY-MM-DD."
				action={
					file ? (
						<Badge variant="outline" className={invalid ? 'text-negative' : 'text-positive'}>
							{preview.isPending
								? 'Validating'
								: invalid
									? 'Needs attention'
									: result
										? 'Imported'
										: 'Ready to import'}
						</Badge>
					) : undefined
				}
			>
				{result ? (
					<div
						role="status"
						className="border-positive/35 bg-positive-muted/25 mb-4 flex flex-col gap-4 rounded-lg border p-4 sm:flex-row sm:items-center sm:justify-between"
					>
						<div className="flex min-w-0 items-start gap-3">
							<span className="bg-positive text-positive-foreground flex size-9 shrink-0 items-center justify-center rounded-full">
								<CheckCircle2 className="size-5" />
							</span>
							<div className="min-w-0">
								<p className="font-semibold">Portfolio created successfully</p>
								<p className="text-muted-foreground mt-0.5 text-sm">
									{result.portfolio.name} · {result.tradesCreated} trades ·{' '}
									{result.positions.length} positions
								</p>
							</div>
						</div>
						<Button onClick={() => router.push('/dashboard')} className="shrink-0">
							Open dashboard <ArrowRight className="size-4" />
						</Button>
					</div>
				) : null}
				{result && (intelligenceLoading || intelligence) ? (
					<div className="border-border/70 bg-surface-strong/25 mb-4 rounded-lg border p-4">
						<p className="text-sm font-semibold">Your first portfolio reading</p>
						{intelligenceLoading ? (
							<p className="text-muted-foreground mt-2 inline-flex items-center gap-2 text-sm">
								<Loader2 className="size-3.5 animate-spin" /> Connecting valuation, risk, and regime
								data
							</p>
						) : (
							<ul className="text-muted-foreground mt-2 space-y-1 text-sm">
								{intelligence?.executive_summary.slice(0, 3).map((item) => (
									<li key={item}>• {item}</li>
								))}
							</ul>
						)}
					</div>
				) : null}

				<div
					role="button"
					tabIndex={0}
					aria-label={file ? `Selected CSV: ${file.name}. Click to replace.` : 'Select a trade CSV'}
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
						'focus-visible:ring-ring group flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-5 py-8 text-center outline-none transition-all duration-300 focus-visible:ring-2',
						dragging && 'border-primary bg-primary/8 scale-[1.005]',
						!dragging && !file && 'hover:border-primary/45 hover:bg-surface-strong/35',
						file && !invalid && 'border-positive/45 bg-positive-muted/10',
						file && invalid && 'border-negative/45 bg-negative-muted/10'
					)}
				>
					{file ? (
						<div className="animate-in fade-in zoom-in-95 flex max-w-xl flex-col items-center duration-300">
							<span
								className={cn(
									'flex size-12 items-center justify-center rounded-full',
									invalid ? 'bg-negative-muted text-negative' : 'bg-positive-muted text-positive'
								)}
							>
								{invalid ? (
									<FileSpreadsheet className="size-6" />
								) : (
									<FileCheck2 className="size-6" />
								)}
							</span>
							<p className="mt-4 max-w-full truncate text-base font-semibold">{file.name}</p>
							<p className="text-muted-foreground mt-1 text-sm">
								{fileSize(file.size)} · {parsed?.total_rows ?? 0} trade rows ·{' '}
								{parsed?.detected_columns.length ?? 0} columns
							</p>
							{invalid ? (
								<p className="text-negative mt-3 text-sm font-medium">
									{parsed?.errors[0]?.row ? `Row ${parsed.errors[0].row}: ` : ''}
									{parsed?.errors[0]?.message ?? 'CSV validation did not complete.'}
								</p>
							) : (
								<p className="text-positive mt-3 inline-flex items-center gap-1.5 text-sm font-medium">
									<CheckCircle2 className="size-4" /> Required columns verified
								</p>
							)}
							<p className="text-muted-foreground mt-4 text-xs">
								Click or drop another file to replace
							</p>
						</div>
					) : (
						<>
							<span className="bg-surface-strong text-muted-foreground group-hover:text-primary flex size-12 items-center justify-center rounded-full transition-colors duration-300">
								<UploadIcon className="size-5" />
							</span>
							<p className="mt-4 text-sm font-semibold">Drag and drop your CSV here</p>
							<p className="text-muted-foreground mt-1 text-xs">or click to browse</p>
						</>
					)}
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

				{upload.isPending ? (
					<div className="mt-4 space-y-2" aria-live="polite">
						<div className="text-muted-foreground flex items-center justify-between gap-3 text-xs">
							<span className="inline-flex items-center gap-2">
								<Loader2 className="size-3.5 animate-spin" /> Validating trades and calculating
								positions
							</span>
							<span>Processing</span>
						</div>
						<Progress value={72} className="h-1.5" indicatorClassName="upload-progress-indicator" />
					</div>
				) : null}

				<div className="mt-4 flex flex-wrap items-center gap-2">
					{invalid ? (
						<Button
							variant="outline"
							onClick={() => void resolveIssues()}
							disabled={resolveCsv.isPending || preview.isPending || upload.isPending}
						>
							{resolveCsv.isPending ? (
								<>
									<Loader2 className="size-4 animate-spin" /> Resolving issues
								</>
							) : (
								<>
									<Sparkles className="size-4" /> Resolve issues
								</>
							)}
						</Button>
					) : null}
					<Button
						onClick={() => void submit()}
						disabled={
							!file || !parsed?.valid || preview.isPending || upload.isPending || Boolean(result)
						}
					>
						{upload.isPending ? (
							<>
								<Loader2 className="size-4 animate-spin" /> Importing portfolio
							</>
						) : result ? (
							<>
								<CheckCircle2 className="size-4" /> Import complete
							</>
						) : (
							`Import ${parsed?.total_rows ? `${parsed.total_rows} ` : ''}trades`
						)}
					</Button>
					{file ? (
						<Button variant="ghost" onClick={clearFile} disabled={upload.isPending}>
							<X className="size-4" /> {result ? 'Import another file' : 'Clear'}
						</Button>
					) : null}
				</div>

				{resolution ? (
					<div
						role="status"
						className={cn(
							'mt-4 rounded-lg border p-3 text-sm',
							resolution.report.valid
								? 'border-positive/35 bg-positive-muted/15'
								: 'border-warning/35 bg-warning-muted/15'
						)}
					>
						<p className="font-semibold">
							{resolution.report.valid ? 'Automatic repair complete' : 'Manual review still needed'}
						</p>
						<p className="text-muted-foreground mt-1">
							{resolution.changes.length
								? `${resolution.changes.length} deterministic change${resolution.changes.length === 1 ? '' : 's'} applied and revalidated.`
								: 'Latent did not find a change it could apply without guessing.'}
						</p>
						{resolution.changes.length ? (
							<ul className="text-muted-foreground mt-2 space-y-1 text-xs">
								{resolution.changes.slice(0, 5).map((change, index) => (
									<li key={`${change.row}-${change.field}-${index}`}>
										{change.row ? `Row ${change.row}, ` : ''}
										{change.field}: {String(change.before ?? 'missing')} →{' '}
										{String(change.after ?? 'empty')}
									</li>
								))}
							</ul>
						) : null}
					</div>
				) : null}
			</SectionCard>

			{parsed ? (
				<SectionCard
					title="Data preview"
					description={`${parsed.detected_columns.length} columns detected · showing first ${parsed.preview.length} of ${parsed.total_rows} rows`}
					action={
						invalid ? (
							<span className="text-negative inline-flex items-center gap-1 text-xs font-medium">
								<X className="size-3.5" /> Review schema
							</span>
						) : (
							<span className="text-positive inline-flex items-center gap-1 text-xs font-medium">
								<CheckCircle2 className="size-3.5" /> Schema valid
							</span>
						)
					}
				>
					{Object.keys(parsed.column_mapping).length ? (
						<div className="mb-3 flex flex-wrap gap-1.5">
							{Object.entries(parsed.column_mapping).map(([from, to]) => (
								<Badge key={from} variant="outline">
									{from} → {to}
								</Badge>
							))}
						</div>
					) : null}
					{parsed.errors.length || parsed.warnings.length ? (
						<div className="mb-3 space-y-1 text-sm">
							{[...parsed.errors, ...parsed.warnings].slice(0, 8).map((issue, index) => (
								<p
									key={`${issue.row}-${issue.field}-${index}`}
									className={index < parsed.errors.length ? 'text-negative' : 'text-warning'}
								>
									{issue.row ? `Row ${issue.row}: ` : ''}
									{issue.message}
								</p>
							))}
						</div>
					) : null}
					<div className="overflow-x-auto rounded-lg border">
						<table className="w-full text-xs">
							<thead className="bg-surface-strong/60">
								<tr>
									{parsed.normalized_columns.map((header) => (
										<th key={header} className="px-3 py-2 text-left font-semibold uppercase">
											{header}
										</th>
									))}
								</tr>
							</thead>
							<tbody>
								{parsed.preview.map((row, rowIndex) => (
									<tr key={rowIndex} className="border-t">
										{parsed.normalized_columns.map((header) => (
											<td key={header} className="num whitespace-nowrap px-3 py-1.5">
												{String(row[header] ?? '')}
											</td>
										))}
									</tr>
								))}
							</tbody>
						</table>
					</div>
				</SectionCard>
			) : null}

			<SectionCard
				title="Expected format"
				description="Required fields are marked with an asterisk."
			>
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
		</div>
	);
}
