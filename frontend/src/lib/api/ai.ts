import { api } from '@/lib/api';
import type { AIReport, Citation } from '@/lib/types';

export type AIProvider = 'openai' | 'gemini' | 'claude' | 'nvidia';

export type AIProviderConfig = {
	default_provider: AIProvider;
	managed_provider: 'nvidia';
	managed_provider_configured: boolean;
	managed_model: string;
};

export type RetrievalMetadata = {
	strategy: 'local_hash_embeddings';
	selected_sources: string[];
	selected_documents: number;
	available_documents: number;
	context_characters: number;
	estimated_input_tokens: number;
	external_embedding_tokens: number;
};

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
	response_mode: 'provider' | 'local' | 'local_fallback';
	tools_used: string[];
	citations: Citation[];
	data_as_of?: string | null;
	provider_error?: string | null;
	retrieval?: RetrievalMetadata | null;
};

export function askCopilot(input: {
	provider: AIProvider;
	apiKey?: string;
	model?: string;
	prompt: string;
	portfolioId: string;
	history: CopilotMessageInput[];
}) {
	return api.post<CopilotAIResponse>('/ai/copilot/chat', {
		portfolio_id: Number(input.portfolioId),
		provider: input.provider,
		api_key: input.apiKey || undefined,
		model: input.model,
		prompt: input.prompt,
		history: input.history
	});
}

export function validateAIProvider(input: {
	provider: AIProvider;
	apiKey?: string;
	model?: string;
}) {
	return api.post<{ valid: boolean; provider: string; model: string }>('/ai/provider/validate', {
		provider: input.provider,
		api_key: input.apiKey || undefined,
		model: input.model
	});
}

export function getAIProviderConfig() {
	return api.get<AIProviderConfig>('/ai/provider/config');
}

export function generateAIReport(input: {
	portfolioId: string;
	reportType: string;
	provider: AIProvider;
	apiKey?: string;
	model?: string;
}) {
	return api.post<AIReport>('/ai/reports', {
		portfolio_id: Number(input.portfolioId),
		report_type: input.reportType,
		provider: input.provider,
		api_key: input.apiKey || undefined,
		model: input.model
	});
}

export function listAIReports(portfolioId: string) {
	return api.get<AIReport[]>(`/ai/reports/${portfolioId}`);
}
