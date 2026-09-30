'use client';

import {
	Bot,
	ArrowUpRight,
	ListChecks,
	Sparkles,
	Clipboard,
	Download,
	FileText,
	KeyRound,
	Printer,
	RefreshCw,
	Send,
	ShieldCheck,
	Trash2
} from 'lucide-react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';

import { SectionCard } from '@/components/charts/chart-card';
import { MarkdownResponse } from '@/components/common/markdown-response';
import { EmptyState, ErrorState } from '@/components/common/states';
import { RequirePortfolio } from '@/components/layout/require-portfolio';
import { PageHeader } from '@/components/layout/top-bar';
import { Badge } from '@/components/ui/badge';
import {
	Accordion,
	AccordionContent,
	AccordionItem,
	AccordionTrigger
} from '@/components/ui/accordion';
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
	type CopilotAIResponse,
	type CopilotTask
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
		| 'next_action'
		| 'data_checks'
		| 'safety'
		| 'elapsed_ms'
	>;
};

export default function AiCopilotRoutePage() {
	return (
		<RequirePortfolio label="the AI copilot">
			{(id) => <Copilot key={id} portfolioId={id} />}
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
	const [sendError, setSendError] = useState<unknown>(null);
	const [lastTask, setLastTask] = useState<CopilotTask>('question');
	const [isValidating, setIsValidating] = useState(false);
	const [connection, setConnection] = useState<'local' | 'unverified' | 'connected'>('local');
	const [managedConfigured, setManagedConfigured] = useState<boolean | null>(null);
	const conversationRef = useRef<HTMLDivElement>(null);
	const followConversation = useRef(true);
	const serverManaged = provider === 'nvidia';

	useEffect(() => {
		const savedProvider = window.sessionStorage.getItem(PROVIDER_STORAGE);
		const storedProvider: AIProvider =
			savedProvider && savedProvider in DEFAULT_MODELS ? (savedProvider as AIProvider) : 'nvidia';
		window.sessionStorage.removeItem(KEY_STORAGE);
		setProvider(storedProvider);
		setApiKey('');
		setModel(
			storedProvider === 'nvidia' ? '' : (window.sessionStorage.getItem(MODEL_STORAGE) ?? '')
		);
		setConnection(storedProvider === 'nvidia' ? 'unverified' : 'local');
		window.localStorage.removeItem('rapra.copilotApiKey');
		void getAIProviderConfig()
			.then((config) => {
				setManagedConfigured(config.managed_provider_configured);
				if (storedProvider === config.managed_provider) {
					setConnection('unverified');
				}
			})
			.catch(() => setManagedConfigured(null));
	}, []);

	useEffect(() => {
		const prompt = searchParams.get('prompt');
		if (prompt) setInput(prompt.slice(0, 4000));
	}, [searchParams]);

	useEffect(() => {
		const frame = window.requestAnimationFrame(() => {
			const conversation = conversationRef.current;
			if (!conversation || !followConversation.current) return;
			conversation.scrollTo({
				top: conversation.scrollHeight,
				behavior:
					messages.length > 1 && !window.matchMedia('(prefers-reduced-motion: reduce)').matches
						? 'smooth'
						: 'auto'
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
		toast.success('Provider key cleared.');
	};

	const send = async (question: string, task: CopilotTask = 'question') => {
		const trimmed = question.trim();
		if (!trimmed || isSending) return;
		setSendError(null);
		setLastTask(task);
		followConversation.current = true;
		const questionId = `u-${Date.now()}`;
		setInput('');
		const history = messages
			.filter((message) => message.role === 'user')
			.slice(-6)
			.map(({ role, content }) => ({ role, content }));
		setMessages((current) => [...current, { id: questionId, role: 'user', content: trimmed }]);
		setIsSending(true);
		try {
			const response = await askCopilot({
				portfolioId,
				provider,
				apiKey: serverManaged ? undefined : apiKey.trim(),
				model: serverManaged ? undefined : model.trim() || undefined,
				prompt: trimmed,
				history,
				task
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
				toast.warning(
					response.safety?.output_status === 'rejected'
						? 'The AI answer did not pass the checks. Showing a local explanation.'
						: 'AI is unavailable. Showing a local explanation.'
				);
			}
		} catch (error) {
			setInput(trimmed);
			setMessages((current) => current.filter((message) => message.id !== questionId));
			setSendError(error);
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
				description="Ask about this portfolio. Answers use your recorded holdings and available analytics."
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
								? 'Local explanation available'
								: serverManaged && managedConfigured
									? 'Managed AI configured'
									: 'Local grounded mode'}
					</Badge>
				}
			/>

			<Accordion type="single" collapsible>
				<AccordionItem value="connection">
					<AccordionTrigger>AI connection & limitations</AccordionTrigger>
					<AccordionContent>
						<p className="text-muted-foreground mb-4 text-sm leading-6">
							State-fit probability is not forecast accuracy. Modeled returns are not your actual
							investment performance. Latent AI uses a server-managed key; personal provider keys
							are optional and stay in this tab.
						</p>
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
										setConnection(next === 'nvidia' ? 'unverified' : 'local');
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
											: 'Cleared when this page is reloaded'
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
								: 'Your key is held in memory, not browser storage. Reloading or leaving this page clears it.'}
						</p>
						<p className="text-muted-foreground mt-2 text-xs">
							AI receives selected portfolio facts and recent questions. Raw CSV files, account
							details and notes are excluded. Your selected provider may process or retain this
							information under its own policies. Never paste passwords or keys into chat. Data
							checks stay local to Latent.
						</p>
					</AccordionContent>
				</AccordionItem>
			</Accordion>

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
								role="log"
								aria-label="Portfolio conversation"
								onScroll={(event) => {
									const element = event.currentTarget;
									followConversation.current =
										element.scrollHeight - element.scrollTop - element.clientHeight < 80;
								}}
								className="mb-3 h-[min(30dvh,18rem)] min-h-40 overflow-y-auto rounded-lg border p-3 sm:h-[min(42dvh,26rem)]"
								aria-live="polite"
							>
								{messages.length === 0 ? (
									<div className="flex h-full flex-col items-center justify-center gap-3 text-center">
										<Bot className="text-muted-foreground size-8" />
										<p className="text-sm font-medium">Make sense of your portfolio</p>
										<p className="text-muted-foreground max-w-sm text-xs">
											A short brief, with the figures behind it. No trades or changes to your
											holdings.
										</p>
										<Button
											size="sm"
											onClick={() => void send('Give me a portfolio brief.', 'brief')}
											disabled={isSending}
										>
											<Sparkles className="size-4" /> Review my portfolio
										</Button>
									</div>
								) : (
									<div className="space-y-4">
										{messages.map((message) => (
											<ChatBubble key={message.id} message={message} />
										))}
									</div>
								)}
							</div>
							{sendError ? (
								<ErrorState
									error={sendError}
									onRetry={() => void send(input, lastTask)}
									className="mb-3"
								/>
							) : null}
							{isSending ? (
								<p role="status" className="text-muted-foreground mb-2 text-xs">
									Preparing an explanation from your portfolio...
								</p>
							) : null}
							<div className="flex gap-2">
								<Textarea
									value={input}
									aria-label="Your question"
									maxLength={4000}
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

						<SectionCard title="Start with a question" className="min-w-0">
							<div className="grid gap-2">
								<Button
									variant="outline"
									className="justify-start"
									disabled={isSending}
									onClick={() => void send('Check whether my data is ready to use.', 'data_check')}
								>
									<ListChecks className="size-4" /> Check my data
								</Button>
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
									onClick={() => {
										setMessages([]);
										setSendError(null);
										setInput('');
									}}
									disabled={isSending}
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
					message.metadata?.data_checks?.length ? (
						<div>
							<h3 className="font-medium">Data readiness</h3>
							<p className="text-muted-foreground mt-1">
								Local checks of stored data, not a guarantee of accuracy.
							</p>
						</div>
					) : (
						<MarkdownResponse content={message.content} />
					)
				) : (
					message.content
				)}
				{message.metadata ? (
					<div className="border-border/70 text-muted-foreground mt-3 space-y-2 border-t pt-2 text-xs">
						<div className="flex flex-wrap items-center gap-2">
							<Badge variant="outline">
								{message.metadata.response_mode === 'provider'
									? 'AI interpretation'
									: 'Local explanation'}
							</Badge>
							{message.metadata.data_as_of ? (
								<span>Data {formatDate(message.metadata.data_as_of)}</span>
							) : null}
						</div>
						{message.metadata.data_checks?.map((check) => (
							<div key={check.label} className="border-b py-2 last:border-0">
								<div className="flex flex-wrap items-center justify-between gap-2">
									<span className="text-foreground font-medium">{check.label}</span>
									<Badge variant="outline">
										{check.status === 'available' ? 'Available' : 'Needs review'}
									</Badge>
								</div>
								<p className="mt-1 leading-relaxed">{check.detail}</p>
								{check.status === 'needs_review' ? (
									<Button asChild variant="link" size="sm" className="h-auto px-0 py-1">
										<Link href={check.href}>
											Review {check.label.toLowerCase()} <ArrowUpRight className="size-3" />
										</Link>
									</Button>
								) : null}
							</div>
						))}
						{message.metadata.next_action ? (
							<Button
								asChild
								variant="outline"
								size="sm"
								className="h-auto max-w-full whitespace-normal text-left"
							>
								<Link href={message.metadata.next_action.href}>
									{message.metadata.next_action.label}
									<ArrowUpRight className="size-3 shrink-0" />
								</Link>
							</Button>
						) : null}
						{message.metadata.provider_error ? (
							<p className="text-warning">{message.metadata.provider_error}</p>
						) : null}
						<Accordion type="single" collapsible>
							<AccordionItem value="evidence" className="border-0">
								<AccordionTrigger className="py-2 text-xs">
									<span className="flex items-center gap-1.5">
										<ShieldCheck className="size-3.5" /> Evidence & limitations
									</span>
								</AccordionTrigger>
								<AccordionContent className="space-y-3 text-xs">
									<p>
										{message.metadata.safety?.note ??
											'Review the evidence before acting. This is not investment advice.'}
									</p>
									{message.metadata.citations.map((citation, index) => (
										<div key={`${citation.source}-${index}`}>
											<p className="text-foreground font-medium">{citation.label}</p>
											<p className="break-words">{citation.value}</p>
											<p className="mt-0.5">Source: {citation.source.replaceAll('_', ' ')}</p>
										</div>
									))}
									{message.metadata.retrieval ? (
										<p>
											Local vector retrieval selected{' '}
											{message.metadata.retrieval.selected_documents} of{' '}
											{message.metadata.retrieval.available_documents} context blocks ·
											approximately {message.metadata.retrieval.estimated_input_tokens} input tokens
											· {message.metadata.retrieval.external_embedding_tokens} embedding API tokens
										</p>
									) : null}
									<p>
										{message.metadata.response_mode === 'provider'
											? message.metadata.model
											: 'No model-generated answer shown'}
										{message.metadata.elapsed_ms !== undefined
											? ` · ${(message.metadata.elapsed_ms / 1000).toFixed(1)}s`
											: ''}
									</p>
								</AccordionContent>
							</AccordionItem>
						</Accordion>
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
