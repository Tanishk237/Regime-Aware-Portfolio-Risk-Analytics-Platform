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
import { buildCopilotResponse, buildReport, COPILOT_STARTERS, REPORT_TYPES } from '@/lib/copilot';
import { usePositions, useRegime, useRisk, useSummary } from '@/lib/queries';

const KEY_STORAGE = 'rapra.copilotApiKey';
const PROVIDER_STORAGE = 'rapra.copilotProvider';

type Provider = 'openai' | 'gemini' | 'claude';
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
	const [provider, setProvider] = useState<Provider>('openai');
	const [apiKey, setApiKey] = useState('');
	const [messages, setMessages] = useState<ChatMessage[]>([]);
	const [input, setInput] = useState('');
	const [reportType, setReportType] = useState(REPORT_TYPES[0] ?? 'Daily Report');
	const [report, setReport] = useState('');

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
		setProvider((window.localStorage.getItem(PROVIDER_STORAGE) as Provider | null) ?? 'openai');
		setApiKey(window.localStorage.getItem(KEY_STORAGE) ?? '');
	}, []);

	const saveConnection = () => {
		if (apiKey.trim().length < 8) {
			toast.error('Enter a valid API key before saving.');
			return;
		}
		window.localStorage.setItem(KEY_STORAGE, apiKey.trim());
		window.localStorage.setItem(PROVIDER_STORAGE, provider);
		toast.success(`${providerLabel(provider)} key saved locally`);
	};

	const send = (question: string) => {
		const trimmed = question.trim();
		if (!trimmed) return;
		setInput('');
		setMessages((current) => [
			...current,
			{ id: `u-${Date.now()}`, role: 'user', content: trimmed },
			{ id: `a-${Date.now()}`, role: 'assistant', content: buildCopilotResponse(context, trimmed) }
		]);
	};

	const generateReport = () => {
		const next = buildReport(context, reportType);
		setReport(next);
		toast.success(`${reportType} generated`);
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
				<div className="grid gap-3 lg:grid-cols-[12rem_minmax(0,1fr)_auto_auto]">
					<div className="grid gap-1.5">
						<Label className="text-xs">Provider</Label>
						<Select value={provider} onValueChange={(value) => setProvider(value as Provider)}>
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
						<KeyRound className="size-4" /> Validate
					</Button>
					<Button
						className="self-end"
						variant="outline"
						onClick={() => {
							window.localStorage.removeItem(KEY_STORAGE);
							setApiKey('');
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
					<div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
						<SectionCard title="Chat">
							<div className="mb-3 h-[28rem] overflow-y-auto rounded-lg border p-3">
								{messages.length === 0 ? (
									<div className="flex h-full flex-col items-center justify-center gap-3 text-center">
										<Bot className="text-muted-foreground size-8" />
										<p className="text-sm font-medium">Ask a portfolio question</p>
									</div>
								) : (
									<div className="space-y-4">
										{messages.map((message) => (
											<div key={message.id} className={message.role === 'user' ? 'text-right' : ''}>
												<div className="inline-block max-w-[90%] rounded-lg border px-3 py-2 text-left text-sm">
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
									className="min-h-12"
								/>
								<Button onClick={() => send(input)} className="self-end">
									<Send className="size-4" />
								</Button>
							</div>
						</SectionCard>

						<SectionCard title="Suggested prompts">
							<div className="grid gap-2">
								{COPILOT_STARTERS.map((starter) => (
									<Button key={starter} variant="outline" size="sm" onClick={() => send(starter)}>
										{starter}
									</Button>
								))}
								<Button variant="ghost" size="sm" onClick={() => setMessages([])}>
									Clear Chat
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
							<Button onClick={generateReport}>
								<FileText className="size-4" /> Generate
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

function providerLabel(provider: Provider) {
	return provider === 'openai' ? 'OpenAI' : provider === 'gemini' ? 'Gemini' : 'Claude';
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
