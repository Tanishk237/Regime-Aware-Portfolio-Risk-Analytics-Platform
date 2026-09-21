from __future__ import annotations

import math
from typing import Any, Literal, Optional

import httpx
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from src.ai.retrieval import LocalContextRetriever, REGIME_MODEL_DISCLOSURE
from src.api.errors import AppError


Provider = Literal["openai", "gemini", "claude", "nvidia"]


class CopilotAIService:
    DEFAULT_MODELS: dict[Provider, str] = {
        "openai": "gpt-4o-mini",
        "gemini": "gemini-flash-latest",
        "claude": "claude-haiku-4-5-20251001",
        "nvidia": "nvidia/nemotron-3.5-lightning-30b-a3b",
    }
    FALLBACK_MODELS: dict[Provider, tuple[str, ...]] = {
        "openai": ("gpt-4o-mini",),
        "gemini": ("gemini-3.8-flash", "gemini-3.5-flash", "gemini-2.5-flash"),
        "claude": ("claude-sonnet-4-6",),
        "nvidia": ("z-ai/glm-5.3-flash", "z-ai/glm-5.3"),
    }

    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        nvidia_base_url: str = "https://integrate.api.nvidia.com/v1",
        max_output_tokens: int = 700,
        history_messages: int = 6,
        retrieval_top_k: int = 4,
        retrieval_character_budget: int = 6000,
    ):
        self.timeout_seconds = timeout_seconds
        self.nvidia_base_url = nvidia_base_url.rstrip("/")
        self.max_output_tokens = max(128, max_output_tokens)
        self.history_messages = max(0, history_messages)
        self.retriever = LocalContextRetriever(
            top_k=retrieval_top_k,
            character_budget=retrieval_character_budget,
        )

    async def generate(
        self,
        *,
        provider: Provider,
        api_key: Optional[str],
        prompt: str,
        context: dict[str, Any],
        history: Optional[list[dict[str, str]]] = None,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        clean_key = (api_key or "").strip()
        if len(clean_key) < 8:
            raise AppError(
                "A valid provider API key is required.",
                code="AI_API_KEY_REQUIRED",
                status_code=422,
            )

        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise AppError(
                "A prompt is required.",
                code="AI_PROMPT_REQUIRED",
                status_code=422,
            )

        selected_model = model or self.DEFAULT_MODELS[provider]
        retrieval = self.retriever.retrieve(clean_prompt, context)
        system_prompt = self._system_prompt(retrieval.context)
        try:
            if provider in {"openai", "nvidia"}:
                answer = await self._openai_compatible(
                    api_key=clean_key,
                    base_url=(
                        "https://api.openai.com/v1"
                        if provider == "openai"
                        else self.nvidia_base_url
                    ),
                    model=selected_model,
                    system_prompt=system_prompt,
                    prompt=clean_prompt,
                    history=history or [],
                    extra_body=(
                        {"chat_template_kwargs": {"enable_thinking": False}}
                        if provider == "nvidia"
                        else None
                    ),
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    if provider == "gemini":
                        answer = await self._gemini(
                            client,
                            api_key=clean_key,
                            model=selected_model,
                            system_prompt=system_prompt,
                            prompt=clean_prompt,
                            history=history or [],
                        )
                    else:
                        answer = await self._claude(
                            client,
                            api_key=clean_key,
                            model=selected_model,
                            system_prompt=system_prompt,
                            prompt=clean_prompt,
                            history=history or [],
                        )
        except AppError:
            raise
        except httpx.HTTPStatusError as exc:
            raise AppError(
                "The selected AI provider rejected the request.",
                code="AI_PROVIDER_ERROR",
                status_code=502,
                details={
                    "provider": provider,
                    "status_code": exc.response.status_code,
                },
            ) from exc
        except httpx.HTTPError as exc:
            raise AppError(
                "The selected AI provider is temporarily unavailable.",
                code="AI_PROVIDER_UNAVAILABLE",
                status_code=502,
                details={"provider": provider, "error_type": type(exc).__name__},
            ) from exc
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            raise AppError(
                (
                    "The selected AI provider rejected the request."
                    if status_code
                    else "The selected AI provider is temporarily unavailable."
                ),
                code="AI_PROVIDER_ERROR" if status_code else "AI_PROVIDER_UNAVAILABLE",
                status_code=502,
                details={
                    "provider": provider,
                    "status_code": status_code,
                    "error_type": type(exc).__name__,
                },
            ) from exc

        retrieval_metadata = retrieval.metadata()
        history_characters = sum(
            len(str(message.get("content") or ""))
            for message in self._recent_history(history or [])
        )
        retrieval_metadata["estimated_input_tokens"] = math.ceil(
            (len(system_prompt) + len(clean_prompt) + history_characters) / 4
        )
        return {
            "provider": provider,
            "model": selected_model,
            "answer": answer,
            "fallback_used": False,
            "retrieval": retrieval_metadata,
        }

    @staticmethod
    def _system_prompt(context: str) -> str:
        return (
            "You are Latent, an AI copilot for portfolio regime and risk analytics. "
            "Use only the supplied controlled tool results as your source of truth. "
            "Explain risk, regime, P&L, concentration, and recommendations clearly. "
            "Never recalculate or alter supplied financial values. "
            "Do not invent market data that is not present. "
            "When data is missing or fallback analytics were used, say so plainly. "
            f"Always preserve this model limitation: {REGIME_MODEL_DISCLOSURE} "
            "Separate observed facts from interpretation and avoid individualized financial advice. "
            f"\n\nRetrieved controlled context:\n{context}"
        )

    def _recent_history(self, history: list[dict[str, str]]) -> list[dict[str, str]]:
        if self.history_messages == 0:
            return []
        return history[-self.history_messages :]

    def _messages(
        self,
        system_prompt: str,
        prompt: str,
        history: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": system_prompt}]
        for message in self._recent_history(history):
            role = message.get("role")
            content = message.get("content")
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def _openai_compatible(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        system_prompt: str,
        prompt: str,
        history: list[dict[str, str]],
        extra_body: Optional[dict[str, Any]] = None,
    ) -> str:
        model_client = ChatOpenAI(
            model=model,
            api_key=SecretStr(api_key),
            base_url=base_url,
            temperature=0.3,
            top_p=1,
            max_tokens=self.max_output_tokens,
            timeout=self.timeout_seconds,
            max_retries=1,
            stream_usage=False,
            extra_body=extra_body,
        )
        history_messages = []
        for message in self._recent_history(history):
            content = str(message.get("content") or "").strip()
            if not content:
                continue
            if message.get("role") == "assistant":
                history_messages.append(AIMessage(content=content))
            elif message.get("role") == "user":
                history_messages.append(HumanMessage(content=content))
        template = ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                MessagesPlaceholder("history"),
                ("human", "{prompt}"),
            ]
        )
        result = await (template | model_client).ainvoke(
            {
                "system_prompt": system_prompt,
                "history": history_messages,
                "prompt": prompt,
            }
        )
        content = result.content
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            text = "".join(
                str(item.get("text", "")) if isinstance(item, dict) else str(item)
                for item in content
            ).strip()
            if text:
                return text
        raise self._invalid_provider_payload("openai-compatible", {"content": content})

    async def _gemini(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        prompt: str,
        history: list[dict[str, str]],
    ) -> str:
        contents = []
        for message in self._recent_history(history):
            role = "model" if message.get("role") == "assistant" else "user"
            content = message.get("content")
            if content:
                contents.append({"role": role, "parts": [{"text": content}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/{self._gemini_model_resource(model)}:generateContent",
            headers={"x-goog-api-key": api_key},
            json={
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": self.max_output_tokens,
                },
            },
        )
        response.raise_for_status()
        payload = response.json()
        try:
            return str(payload["candidates"][0]["content"]["parts"][0]["text"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise self._invalid_provider_payload("gemini", payload) from exc

    async def _claude(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        prompt: str,
        history: list[dict[str, str]],
    ) -> str:
        messages = [
            {"role": item["role"], "content": item["content"]}
            for item in self._messages("", prompt, history)
            if item["role"] in {"user", "assistant"} and item["content"]
        ]
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": model,
                "system": system_prompt,
                "messages": messages,
                "max_tokens": self.max_output_tokens,
                "temperature": 0.3,
            },
        )
        response.raise_for_status()
        payload = response.json()
        try:
            return str(payload["content"][0]["text"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise self._invalid_provider_payload("claude", payload) from exc

    @staticmethod
    def _invalid_provider_payload(provider: Provider, payload: dict[str, Any]) -> AppError:
        return AppError(
            "The selected AI provider returned an unexpected response.",
            code="AI_PROVIDER_INVALID_RESPONSE",
            status_code=502,
            details={"provider": provider},
        )

    @staticmethod
    def _gemini_model_resource(model: str) -> str:
        normalized = model.strip().removeprefix("models/")
        return f"models/{normalized}"
