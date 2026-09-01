import { api } from '@/lib/api';
import type { CopilotContext } from '@/lib/copilot';

export type AIProvider = 'openai' | 'gemini' | 'claude';

export type CopilotMessageInput = {
	role: 'user' | 'assistant';
	content: string;
};

export type CopilotAIResponse = {
	success: boolean;
	provider: AIProvider;
	model: string;
	answer: string;
	fallback_used: boolean;
};

export function askCopilot(input: {
	provider: AIProvider;
	apiKey: string;
	model?: string;
	prompt: string;
	context: CopilotContext;
	history: CopilotMessageInput[];
}) {
	return api.post<CopilotAIResponse>('/ai/copilot/chat', {
		provider: input.provider,
		api_key: input.apiKey,
		model: input.model,
		prompt: input.prompt,
		context: input.context,
		history: input.history
	});
}
