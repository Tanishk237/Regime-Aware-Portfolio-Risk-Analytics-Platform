'use client';

import {
	Bot,
	Clipboard,
	Download,
	FileText,
	Info,
	KeyRound,
	Printer,
	RefreshCw,
	Send,
	ShieldCheck,
	Trash2
} from 'lucide-react';
import { useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';

import { SectionCard } from '@/components/charts/chart-card';
import { MarkdownResponse } from '@/components/common/markdown-response';
import { EmptyState, ErrorState } from '@/components/common/states';
import { RequirePortfolio } from '@/components/layout/require-portfolio';
import { PageHeader } from '@/components/layout/top-bar';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { errorMessage } from '@/lib/api';
import {
	askCopilot,
	getAIProviderConfig,
	validateAIProvider,
	type AIProvider,
	type CopilotAIResponse
} from '@/lib/api/ai';
import { COPILOT_STARTERS, REPORT_TYPES } from '@/lib/copilot';
import { formatDate } from '@/lib/format';
import { useAIReports } from '@/lib/queries';

const KEY_STORAGE = 'latent.copilotApiKey';
const PROVIDER_STORAGE = 'latent.copilotProvider';
const MODEL_STORAGE = 'latent.copilotModel';

const DEFAULT_MODELS: Record<AIProvider, string> = {
	openai: 'gpt-4o-mini',
	gemini: 'gemini-flash-latest',
	claude: 'claude-haiku-4-5-20251001',
	nvidia: 'nvidia/nemotron-3.5-lightning-30b-a3b'
};

type ChatMessage = {
	id: string;
	role: 'user' | 'assistant';
	content: string;
	metadata?: Pick<
		CopilotAIResponse,
		| 'response_mode'
		| 'provider'
		| 'model'
		| 'tools_used'
		| 'citations'
		| 'data_as_of'
		| 'provider_error'
		| 'retrieval'
	>;
};

export default function AiCopilotRoutePage() {
	return (
		<RequirePortfolio label="the AI copilot">
			{(id) => <Copilot portfolioId={id} />}
		</RequirePortfolio>
	);
}

function Copilot({ portfolioId }: { portfolioId: string }) {
	const searchParams = useSearchParams();
	const reports = useAIReports(portfolioId);
	const [provider, setProvider] = useState<AIProvider>('nvidia');
	const [apiKey, setApiKey] = useState('');
	const [model, setModel] = useState('');
	const [messages, setMessages] = useState<ChatMessage[]>([]);
	const [input, setInput] = useState('');
	const [reportType, setReportType] = useState(REPORT_TYPES[0] ?? 'Daily Report');
	const [report, setReport] = useState('');
	const [isSending, setIsSending] = useState(false);
	const [isValidating, setIsValidating] = useState(false);
	const [connection, setConnection] = useState<'local' | 'unverified' | 'connected'>('local');
	const [managedConfigured, setManagedConfigured] = useState<boolean | null>(null);
	const conversationRef = useRef<HTMLDivElement>(null);
	const serverManaged = provider === 'nvidia';

	useEffect(() => {
		const storedProvider =
			(window.sessionStorage.getItem(PROVIDER_STORAGE) as AIProvider | null) ?? 'nvidia';
		const storedKey = window.sessionStorage.getItem(KEY_STORAGE) ?? '';
		setProvider(storedProvider);
		setApiKey(storedProvider === 'nvidia' ? '' : storedKey);
		setModel(
			storedProvider === 'nvidia' ? '' : (window.sessionStorage.getItem(MODEL_STORAGE) ?? '')
		);
		setConnection(storedProvider === 'nvidia' || storedKey ? 'unverified' : 'local');
		window.localStorage.removeItem('rapra.copilotApiKey');
		void getAIProviderConfig()
			.then((config) => {
				setManagedConfigured(config.managed_provider_configured);
				if (storedProvider === config.managed_provider) {
					setConnection(config.managed_provider_configured ? 'connected' : 'unverified');
				}
			})
			.catch(() => setManagedConfigured(null));
	}, []);

	useEffect(() => {
		const prompt = searchParams.get('prompt');
		if (prompt) setInput(prompt.slice(0, 12000));
	}, [searchParams]);

	useEffect(() => {
		const frame = window.requestAnimationFrame(() => {
			const conversation = conversationRef.current;
			if (!conversation) return;
			conversation.scrollTo({
				top: conversation.scrollHeight,
				behavior: messages.length > 1 ? 'smooth' : 'auto'
			});
		});
		return () => window.cancelAnimationFrame(frame);
	}, [isSending, messages]);

	const validateConnection = async () => {
		if (!serverManaged && apiKey.trim().length < 8) {
			toast.error('Enter a provider API key before validating.');
			return;
		}
		setIsValidating(true);
		try {
			const result = await validateAIProvider({
				provider,
				apiKey: serverManaged ? undefined : apiKey.trim(),
				model: serverManaged ? undefined : model.trim() || undefined
			});
			if (serverManaged) {
				window.sessionStorage.removeItem(KEY_STORAGE);
				window.sessionStorage.removeItem(MODEL_STORAGE);
				setModel('');
			} else {
				window.sessionStorage.setItem(KEY_STORAGE, apiKey.trim());
				window.sessionStorage.setItem(MODEL_STORAGE, result.model);
				setModel(result.model);
			}
			window.sessionStorage.setItem(PROVIDER_STORAGE, provider);
			setConnection('connected');
			toast.success(`${providerLabel(provider)} connection validated for this tab.`);
		} catch (error) {
			setConnection('unverified');
			toast.error(errorMessage(error));
		} finally {
			setIsValidating(false);
		}
	};

	const clearConnection = () => {
		window.sessionStorage.removeItem(KEY_STORAGE);
		window.sessionStorage.removeItem(MODEL_STORAGE);
		setApiKey('');
		setModel('');
		setConnection('local');
		toast.success('Browser-stored provider key removed from this tab.');
	};

	const send = async (question: string) => {
		const trimmed = question.trim();
		if (!trimmed || isSending) return;
		setInput('');
		const history = messages.map(({ role, content }) => ({ role, content }));
		setMessages((current) => [
			...current,
			{ id: `u-${Date.now()}`, role: 'user', content: trimmed }
		]);
		setIsSending(true);
		try {
			const response = await askCopilot({
				portfolioId,
				provider,
				apiKey: serverManaged ? undefined : apiKey.trim(),
				model: serverManaged ? undefined : model.trim() || undefined,
				prompt: trimmed,
				history
			});
			setMessages((current) => [
				...current,
				{
					id: `a-${Date.now()}`,
					role: 'assistant',
					content: response.answer,
					metadata: response
				}
			]);
			if (response.response_mode === 'local_fallback') {
				toast.warning('Provider failed. Latent returned a grounded local explanation instead.');
			}
		} catch (error) {
			toast.error(errorMessage(error));
		} finally {
			setIsSending(false);
		}
	};

	const generateReport = async () => {
		try {
			const next = await reports.generate.mutateAsync({
				reportType,
				provider,
				apiKey: serverManaged ? undefined : apiKey.trim() || undefined,
				model: serverManaged ? undefined : model.trim() || undefined
			});
			setReport(next.content);
			toast.success(`${reportType} generated from current backend analytics.`);
		} catch (error) {
			toast.error(errorMessage(error));
		}
	};

	return (
		<div className="space-y-4">
			<PageHeader
				title="AI Copilot"
				description="Ask grounded questions and generate reports from authenticated portfolio tools."
				actions={
					<Badge variant="outline" className="gap-1.5">
						<span
							className={
								connection === 'connected'
									? 'bg-positive size-1.5 rounded-full'
									: 'bg-muted-foreground size-1.5 rounded-full'
							}
						/>
						{connection === 'connected'
							? serverManaged
								? 'Latent AI ready'
								: `${providerLabel(provider)} connected`
							: serverManaged && managedConfigured === false
								? 'Latent AI unavailable'
								: 'Local grounded mode'}
					</Badge>
				}
			/>

			<Alert className="border-sky-500/20 bg-sky-500/[0.04]">
				<Info className="size-4 text-sky-400" />
				<AlertTitle>How to read state fit probability</AlertTitle>
				<AlertDescription className="text-muted-foreground">
					HMM probability measures how well current observations fit an inferred state. It is not
					forecast accuracy or the probability of the next market move. Predictive accuracy remains
					unverified until time-ordered walk-forward validation is completed against independent
					regime labels.
				</AlertDescription>
			</Alert>

			<SectionCard
				title="AI connection"
				description="Latent AI is the managed default. Switch providers only when you want to use your own tab-scoped key."
			>
				<div className="grid gap-3 lg:grid-cols-[11rem_minmax(12rem,18rem)_minmax(0,1fr)_auto_auto]">
					<div className="grid gap-1.5">
						<Label className="text-xs">Provider</Label>
						<Select
							value={provider}
							onValueChange={(value) => {
								const next = value as AIProvider;
								setProvider(next);
								window.sessionStorage.setItem(PROVIDER_STORAGE, next);
								setModel('');
								setApiKey('');
								window.sessionStorage.removeItem(KEY_STORAGE);
								setConnection(
									next === 'nvidia' && managedConfigured
										? 'connected'
										: next === 'nvidia'
											? 'unverified'
											: 'local'
								);
							}}
						>
							<SelectTrigger>
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="nvidia">Latent AI (managed)</SelectItem>
								<SelectItem value="openai">OpenAI</SelectItem>
								<SelectItem value="gemini">Gemini</SelectItem>
								<SelectItem value="claude">Claude</SelectItem>
							</SelectContent>
						</Select>
					</div>
					<div className="grid gap-1.5">
						<Label htmlFor="ai-model" className="text-xs">
							Model {serverManaged ? '' : '(optional)'}
						</Label>
						<Input
							id="ai-model"
							value={model}
							disabled={serverManaged}
							onChange={(event) => {
								setModel(event.target.value);
								setConnection(apiKey ? 'unverified' : 'local');
							}}
							placeholder={
								serverManaged
									? 'Selected securely by Latent'
									: `Automatic: ${DEFAULT_MODELS[provider]}`
							}
						/>
					</div>
					<div className="grid gap-1.5">
						<Label htmlFor="api-key" className="text-xs">
							API key
						</Label>
						<Input
							id="api-key"
							type="password"
							autoComplete="off"
							value={serverManaged ? '' : apiKey}
							disabled={serverManaged}
							onChange={(event) => {
								setApiKey(event.target.value);
								setConnection(event.target.value ? 'unverified' : 'local');
							}}
							placeholder={
								serverManaged
									? 'Configured securely on the backend'
									: 'Kept only for this browser tab'
							}
						/>
					</div>
					<Button
						className="self-end"
						onClick={() => void validateConnection()}
						disabled={isValidating}
					>
						{isValidating ? (
							<RefreshCw className="size-4 animate-spin" />
						) : (
							<KeyRound className="size-4" />
						)}
						Validate
					</Button>
					<Button
						className="self-end"
						variant="outline"
						onClick={clearConnection}
						disabled={serverManaged || !apiKey}
					>
						<Trash2 className="size-4" /> Clear
					</Button>
				</div>
				<p className="text-muted-foreground mt-3 text-xs">
					{serverManaged
						? managedConfigured === false
							? 'Latent AI needs a server-side NVIDIA_API_KEY. No credential is ever sent to this browser.'
							: 'Latent AI uses a server-managed NVIDIA key and automatically selects a compatible model. The credential is never sent to this browser.'
						: 'This provider key is tab-scoped and sent to the backend only for the selected request.'}
				</p>
			</SectionCard>

			<Tabs defaultValue="chat">
				<TabsList>
					<TabsTrigger value="chat">Chat</TabsTrigger>
					<TabsTrigger value="reports">Reports</TabsTrigger>
				</TabsList>
				<TabsContent value="chat" className="mt-4">
					<div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
						<SectionCard title="Conversation">
							<div
								ref={conversationRef}
								className="mb-3 h-[30rem] overflow-y-auto rounded-lg border p-3"
								aria-live="polite"
							>
								{messages.length === 0 ? (
									<div className="flex h-full flex-col items-center justify-center gap-3 text-center">
										<Bot className="text-muted-foreground size-8" />
										<p className="text-sm font-medium">Ask a question about this portfolio</p>
										<p className="text-muted-foreground max-w-sm text-xs">
											Latent selects controlled portfolio, risk, regime, position, and profile tools
											based on your question.
										</p>
									</div>
								) : (
									<div className="space-y-4">
										{messages.map((message) => (
											<ChatBubble key={message.id} message={message} />
										))}
									</div>
								)}
							</div>
							<div className="flex gap-2">
								<Textarea
									value={input}
									onChange={(event) => setInput(event.target.value)}
									onKeyDown={(event) => {
										if (event.key === 'Enter' && !event.shiftKey) {
											event.preventDefault();
											void send(input);
										}
									}}
									placeholder="Ask about risk, regime, P&L, or next actions..."
									className="min-h-12 min-w-0"
								/>
								<Button
									size="icon"
									aria-label="Send question"
									onClick={() => void send(input)}
									className="self-end"
									disabled={isSending || !input.trim()}
								>
									{isSending ? (
										<RefreshCw className="size-4 animate-spin" />
									) : (
										<Send className="size-4" />
									)}
								</Button>
							</div>
						</SectionCard>

						<SectionCard title="Suggested prompts" className="min-w-0">
							<div className="grid gap-2">
								{COPILOT_STARTERS.map((starter) => (
									<Button
										key={starter}
										variant="outline"
										size="sm"
										onClick={() => void send(starter)}
										disabled={isSending}
										className="h-auto min-h-10 w-full justify-start whitespace-normal break-words px-3 py-2 text-left leading-snug"
									>
										{starter}
									</Button>
								))}
								<Button
									variant="ghost"
									size="sm"
									onClick={() => setMessages([])}
									className="mt-1 w-full justify-start"
								>
									<Trash2 className="size-3.5" /> Clear chat
								</Button>
							</div>
						</SectionCard>
					</div>
				</TabsContent>

				<TabsContent value="reports" className="mt-4">
					<div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
						<SectionCard
							title="Report builder"
							description="Reports preserve backend values and include their data date."
						>
							<div className="mb-3 flex flex-wrap gap-2">
								<Select value={reportType} onValueChange={setReportType}>
									<SelectTrigger className="w-full sm:w-[14rem]">
										<SelectValue />
									</SelectTrigger>
									<SelectContent>
										{REPORT_TYPES.map((item) => (
											<SelectItem key={item} value={item}>
												{item}
											</SelectItem>
										))}
									</SelectContent>
								</Select>
								<Button onClick={() => void generateReport()} disabled={reports.generate.isPending}>
									{reports.generate.isPending ? (
										<RefreshCw className="size-4 animate-spin" />
									) : (
										<FileText className="size-4" />
									)}{' '}
									Generate
								</Button>
								<Button variant="outline" disabled={!report} onClick={() => void copy(report)}>
									<Clipboard className="size-4" /> Copy
								</Button>
								<Button
									variant="outline"
									disabled={!report}
									onClick={() => download(report, reportType)}
								>
									<Download className="size-4" /> Markdown
								</Button>
								<Button
									variant="outline"
									disabled={!report}
									onClick={() => printReport(reportType)}
								>
									<Printer className="size-4" /> PDF
								</Button>
							</div>
							<div className="min-h-[26rem] rounded-lg border p-4">
								{report ? (
									<MarkdownResponse content={report} />
								) : (
									<EmptyState
										title="No report selected"
										description="Generate a current report or open one from history."
									/>
								)}
							</div>
						</SectionCard>
						<SectionCard title="Report history">
							{reports.isError ? (
								<ErrorState error={reports.error} onRetry={() => void reports.refetch()} />
							) : reports.data?.length ? (
								<div className="space-y-2">
									{reports.data.map((item) => (
										<Button
											key={item.id}
											variant="outline"
											className="h-auto w-full justify-start px-3 py-2 text-left"
											onClick={() => {
												setReport(item.content);
												setReportType(item.report_type);
											}}
										>
											<span className="min-w-0">
												<span className="block truncate text-sm font-medium">{item.title}</span>
												<span className="text-muted-foreground mt-0.5 block text-xs">
													{formatDate(item.created_at)} · {item.response_mode.replace('_', ' ')}
												</span>
											</span>
										</Button>
									))}
								</div>
							) : (
								<EmptyState title="No saved reports" />
							)}
						</SectionCard>
					</div>
				</TabsContent>
			</Tabs>
		</div>
	);
}

function ChatBubble({ message }: { message: ChatMessage }) {
	return (
		<div className={message.role === 'user' ? 'text-right' : ''}>
			<div className="inline-block max-w-[92%] overflow-hidden break-words rounded-lg border px-3 py-2 text-left text-sm">
				{message.role === 'assistant' ? (
					<MarkdownResponse content={message.content} />
				) : (
					message.content
				)}
				{message.metadata ? (
					<div className="border-border/70 text-muted-foreground mt-3 flex flex-wrap items-center gap-1.5 border-t pt-2 text-xs">
						<Badge variant="outline">{message.metadata.response_mode.replace('_', ' ')}</Badge>
						<Badge variant="outline">{message.metadata.model}</Badge>
						{message.metadata.tools_used.map((tool) => (
							<Badge key={tool} variant="secondary">
								{tool.replaceAll('_', ' ')}
							</Badge>
						))}
						{message.metadata.data_as_of ? (
							<span>Data {formatDate(message.metadata.data_as_of)}</span>
						) : null}
						{message.metadata.provider_error ? (
							<p className="text-warning basis-full">
								Provider error: {message.metadata.provider_error}
							</p>
						) : null}
						{message.metadata.retrieval ? (
							<p className="basis-full">
								Local vector retrieval selected {message.metadata.retrieval.selected_documents} of{' '}
								{message.metadata.retrieval.available_documents} context blocks · approximately{' '}
								{message.metadata.retrieval.estimated_input_tokens} input tokens ·{' '}
								{message.metadata.retrieval.external_embedding_tokens} embedding API tokens
							</p>
						) : null}
						{message.metadata.citations.length ? (
							<p className="basis-full">
								<ShieldCheck className="mr-1 inline size-3" /> {message.metadata.citations.length}{' '}
								backend facts cited
							</p>
						) : null}
					</div>
				) : null}
			</div>
		</div>
	);
}

function providerLabel(provider: AIProvider) {
	if (provider === 'openai') return 'OpenAI';
	if (provider === 'gemini') return 'Gemini';
	if (provider === 'claude') return 'Claude';
	return 'NVIDIA';
}

async function copy(content: string) {
	await navigator.clipboard.writeText(content);
	toast.success('Copied');
}

function printReport(title: string) {
	document.title = `${title} - Latent`;
	window.print();
}

function download(content: string, title: string) {
	const blob = new Blob([content], { type: 'text/markdown' });
	const url = URL.createObjectURL(blob);
	const link = document.createElement('a');
	link.href = url;
	link.download = `${title.toLowerCase().replace(/\s+/g, '-')}.md`;
	link.click();
	URL.revokeObjectURL(url);
}
