'use client';

import {
	Bot,
	Clipboard,
	Download,
	FileText,
	KeyRound,
	Printer,
	RefreshCw,
	Send,
	Trash2
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

import { SectionCard } from '@/components/charts/chart-card';
import { MarkdownResponse } from '@/components/common/markdown-response';
import { RequirePortfolio } from '@/components/layout/require-portfolio';
import { PageHeader } from '@/components/layout/top-bar';
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
import { ApiError, errorMessage } from '@/lib/api';
import { askCopilot, type AIProvider } from '@/lib/api/ai';
import {
	buildCopilotResponse,
	buildReport,
	COPILOT_STARTERS,
	REPORT_TYPES,
	type CopilotContext
} from '@/lib/copilot';
import { usePositions, useRegime, useRisk, useSummary } from '@/lib/queries';

const KEY_STORAGE = 'rapra.copilotApiKey';
const PROVIDER_STORAGE = 'rapra.copilotProvider';
const MODEL_STORAGE = 'rapra.copilotModel';

const DEFAULT_MODELS: Record<AIProvider, string> = {
	openai: 'gpt-4o-mini',
	gemini: 'gemini-2.0-flash',
	claude: 'claude-3-5-haiku-latest'
};

type ChatMessage = { id: string; role: 'user' | 'assistant'; content: string };

export default function AiCopilotRoutePage() {
	return (
		<RequirePortfolio label="the AI copilot">
			{(id) => <Copilot portfolioId={id} />}
		</RequirePortfolio>
	);
}

function Copilot({ portfolioId }: { portfolioId: string }) {
	const summary = useSummary(portfolioId);
	const positions = usePositions(portfolioId);
	const risk = useRisk(portfolioId);
	const regime = useRegime(portfolioId);
	const [provider, setProvider] = useState<AIProvider>('openai');
	const [apiKey, setApiKey] = useState('');
	const [model, setModel] = useState(DEFAULT_MODELS.openai);
	const [messages, setMessages] = useState<ChatMessage[]>([]);
	const [input, setInput] = useState('');
	const [reportType, setReportType] = useState(REPORT_TYPES[0] ?? 'Daily Report');
	const [report, setReport] = useState('');
	const [isSending, setIsSending] = useState(false);
	const [isGeneratingReport, setIsGeneratingReport] = useState(false);

	const context = useMemo(
		() => ({
			summary: summary.data,
			positions: positions.data ?? [],
			risk: risk.data,
			regime: regime.data
		}),
		[summary.data, positions.data, risk.data, regime.data]
	);

	useEffect(() => {
		const storedProvider =
			(window.localStorage.getItem(PROVIDER_STORAGE) as AIProvider | null) ?? 'openai';
		setProvider(storedProvider);
		setApiKey(window.localStorage.getItem(KEY_STORAGE) ?? '');
		setModel(window.localStorage.getItem(MODEL_STORAGE) ?? DEFAULT_MODELS[storedProvider]);
	}, []);

	const saveConnection = () => {
		if (apiKey.trim().length < 8) {
			toast.error('Enter a valid API key before saving.');
			return;
		}
		window.localStorage.setItem(KEY_STORAGE, apiKey.trim());
		window.localStorage.setItem(PROVIDER_STORAGE, provider);
		window.localStorage.setItem(MODEL_STORAGE, model.trim() || DEFAULT_MODELS[provider]);
		toast.success(`${providerLabel(provider)} key and model saved locally`);
	};

	const send = async (question: string) => {
		const trimmed = question.trim();
		if (!trimmed || isSending) return;
		setInput('');
		const userMessage: ChatMessage = { id: `u-${Date.now()}`, role: 'user', content: trimmed };
		setMessages((current) => [...current, userMessage]);
		setIsSending(true);
		try {
			const answer = await generateAIAnswer(trimmed, messages, context, provider, apiKey, model);
			setMessages((current) => [
				...current,
				{ id: `a-${Date.now()}`, role: 'assistant', content: answer }
			]);
		} finally {
			setIsSending(false);
		}
	};

	const generateReport = async () => {
		if (isGeneratingReport) return;
		setIsGeneratingReport(true);
		try {
			const prompt = `Generate a ${reportType} for this portfolio. Include portfolio snapshot, risk, regime, top drivers, and recommended next actions.`;
			const next = await generateAIAnswer(prompt, messages, context, provider, apiKey, model, () =>
				buildReport(context, reportType)
			);
			setReport(next);
			toast.success(`${reportType} generated`);
		} finally {
			setIsGeneratingReport(false);
		}
	};

	return (
		<div className="space-y-4">
			<PageHeader
				title="AI Copilot"
				description="Portfolio-aware chat and reports grounded in live backend analytics."
				actions={
					<Button
						size="sm"
						variant="outline"
						onClick={() => {
							void risk.refetch();
							void regime.refetch();
						}}
					>
						<RefreshCw className="size-3.5" /> Refresh Context
					</Button>
				}
			/>

			<SectionCard title="Connection">
				<p className="text-muted-foreground mb-3 text-sm">
					This version uses portfolio analytics to generate grounded answers. Provider keys are
					stored only on this browser and can be connected to backend AI orchestration when that
					service is enabled.
				</p>
				<div className="grid gap-3 lg:grid-cols-[12rem_minmax(12rem,18rem)_minmax(0,1fr)_auto_auto]">
					<div className="grid gap-1.5">
						<Label className="text-xs">Provider</Label>
						<Select
							value={provider}
							onValueChange={(value) => {
								const nextProvider = value as AIProvider;
								setProvider(nextProvider);
								setModel(DEFAULT_MODELS[nextProvider]);
							}}
						>
							<SelectTrigger>
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="openai">OpenAI</SelectItem>
								<SelectItem value="gemini">Gemini</SelectItem>
								<SelectItem value="claude">Claude</SelectItem>
							</SelectContent>
						</Select>
					</div>
					<div className="grid gap-1.5">
						<Label htmlFor="ai-model" className="text-xs">
							Model
						</Label>
						<Input
							id="ai-model"
							value={model}
							onChange={(event) => setModel(event.target.value)}
							placeholder={DEFAULT_MODELS[provider]}
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
							value={apiKey}
							onChange={(event) => setApiKey(event.target.value)}
							placeholder="Stored only in this browser"
						/>
					</div>
					<Button className="self-end" onClick={saveConnection}>
						<KeyRound className="size-4" /> Save Key
					</Button>
					<Button
						className="self-end"
						variant="outline"
						onClick={() => {
							window.localStorage.removeItem(KEY_STORAGE);
							window.localStorage.removeItem(MODEL_STORAGE);
							setApiKey('');
							setModel(DEFAULT_MODELS[provider]);
							toast.success('Key removed');
						}}
					>
						<Trash2 className="size-4" /> Clear
					</Button>
				</div>
			</SectionCard>

			<Tabs defaultValue="chat">
				<TabsList>
					<TabsTrigger value="chat">Chat</TabsTrigger>
					<TabsTrigger value="reports">Reports</TabsTrigger>
				</TabsList>
				<TabsContent value="chat" className="mt-4">
					<div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
						<SectionCard title="Chat">
							<div className="mb-3 h-[28rem] overflow-y-auto rounded-lg border p-3">
								{messages.length === 0 ? (
									<div className="flex h-full flex-col items-center justify-center gap-3 text-center">
										<Bot className="text-muted-foreground size-8" />
										<p className="text-sm font-medium">
											{apiKey ? 'Ask with your connected LLM key' : 'Ask a portfolio question'}
										</p>
									</div>
								) : (
									<div className="space-y-4">
										{messages.map((message) => (
											<div key={message.id} className={message.role === 'user' ? 'text-right' : ''}>
												<div className="inline-block max-w-[90%] overflow-hidden break-words rounded-lg border px-3 py-2 text-left text-sm">
													{message.role === 'assistant' ? (
														<MarkdownResponse content={message.content} />
													) : (
														message.content
													)}
												</div>
											</div>
										))}
									</div>
								)}
							</div>
							<div className="flex gap-2">
								<Textarea
									value={input}
									onChange={(event) => setInput(event.target.value)}
									placeholder="Ask about risk, regime, P&L, recommendations..."
									className="min-h-12 min-w-0"
								/>
								<Button
									size="icon"
									onClick={() => void send(input)}
									className="self-end"
									disabled={isSending}
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
									<Trash2 className="size-3.5" /> Clear Chat
								</Button>
							</div>
						</SectionCard>
					</div>
				</TabsContent>
				<TabsContent value="reports" className="mt-4">
					<SectionCard title="Reports">
						<div className="mb-3 flex flex-wrap gap-2">
							<Select value={reportType} onValueChange={setReportType}>
								<SelectTrigger className="w-[14rem]">
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
							<Button onClick={() => void generateReport()} disabled={isGeneratingReport}>
								{isGeneratingReport ? (
									<RefreshCw className="size-4 animate-spin" />
								) : (
									<FileText className="size-4" />
								)}
								Generate
							</Button>
							<Button variant="outline" disabled={!report} onClick={() => copy(report)}>
								<Clipboard className="size-4" /> Copy
							</Button>
							<Button
								variant="outline"
								disabled={!report}
								onClick={() => download(report, reportType)}
							>
								<Download className="size-4" /> Markdown
							</Button>
							<Button variant="outline" disabled={!report} onClick={() => printReport(reportType)}>
								<Printer className="size-4" /> PDF
							</Button>
						</div>
						<div className="min-h-[26rem] rounded-lg border p-4">
							{report ? (
								<MarkdownResponse content={report} />
							) : (
								<p className="text-muted-foreground text-sm">
									Generate a report to preview it here.
								</p>
							)}
						</div>
					</SectionCard>
				</TabsContent>
			</Tabs>
		</div>
	);
}

async function generateAIAnswer(
	prompt: string,
	messages: ChatMessage[],
	context: CopilotContext,
	provider: AIProvider,
	apiKey: string,
	model: string,
	fallback: () => string = () => buildCopilotResponse(context, prompt)
) {
	const trimmedKey = apiKey.trim();
	if (!trimmedKey) {
		toast.info('No AI key connected. Using local portfolio summary.');
		return fallback();
	}

	try {
		const response = await askCopilot({
			provider,
			apiKey: trimmedKey,
			model: model.trim() || DEFAULT_MODELS[provider],
			prompt,
			context,
			history: messages
				.filter((message) => message.role === 'user' || message.role === 'assistant')
				.map((message) => ({ role: message.role, content: message.content }))
		});
		return response.answer;
	} catch (error) {
		toast.error(errorMessage(error));
		return [
			'## Provider request failed',
			`The ${providerLabel(provider)} call did not complete: ${errorMessage(error)}`,
			providerDebugDetails(error),
			'',
			'## Local fallback',
			fallback()
		]
			.filter(Boolean)
			.join('\n');
	}
}

function providerLabel(provider: AIProvider) {
	return provider === 'openai' ? 'OpenAI' : provider === 'gemini' ? 'Gemini' : 'Claude';
}

function providerDebugDetails(error: unknown) {
	if (!(error instanceof ApiError) || !error.details || typeof error.details !== 'object') {
		return '';
	}
	const details = error.details as Record<string, unknown>;
	const statusCode = details['status_code'] ? `Status: ${String(details['status_code'])}` : '';
	const body = details['body'] ? `Provider response: ${String(details['body'])}` : '';
	return [statusCode, body].filter(Boolean).join('\n');
}

async function copy(content: string) {
	await navigator.clipboard.writeText(content);
	toast.success('Copied');
}

function printReport(title: string) {
	document.title = `${title} - Regime Aware Portfolio Risk Analytics`;
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
