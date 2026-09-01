from __future__ import annotations

from typing import Any, Literal, Optional

import httpx

from src.api.errors import AppError


Provider = Literal["openai", "gemini", "claude"]


class CopilotAIService:
    DEFAULT_MODELS: dict[Provider, str] = {
        "openai": "gpt-4o-mini",
        "gemini": "gemini-2.0-flash",
        "claude": "claude-3-5-haiku-latest",
    }

    def __init__(self, *, timeout_seconds: float = 30.0):
        self.timeout_seconds = timeout_seconds

    async def generate(
        self,
        *,
        provider: Provider,
        api_key: str,
        prompt: str,
        context: dict[str, Any],
        history: Optional[list[dict[str, str]]] = None,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        clean_key = api_key.strip()
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
        system_prompt = self._system_prompt(context)
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                if provider == "openai":
                    answer = await self._openai(
                        client,
                        api_key=clean_key,
                        model=selected_model,
                        system_prompt=system_prompt,
                        prompt=clean_prompt,
                        history=history or [],
                    )
                elif provider == "gemini":
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
                    "body": exc.response.text[:500],
                },
            ) from exc
        except httpx.HTTPError as exc:
            raise AppError(
                "The selected AI provider is temporarily unavailable.",
                code="AI_PROVIDER_UNAVAILABLE",
                status_code=502,
                details={"provider": provider, "error": str(exc)},
            ) from exc

        return {
            "provider": provider,
            "model": selected_model,
            "answer": answer,
            "fallback_used": False,
        }

    @staticmethod
    def _system_prompt(context: dict[str, Any]) -> str:
        return (
            "You are an AI copilot for a portfolio risk analytics dashboard. "
            "Use the supplied portfolio context as your source of truth. "
            "Explain risk, regime, P&L, concentration, and recommendations clearly. "
            "Do not invent market data that is not present. "
            "When data is missing or fallback analytics were used, say so plainly. "
            f"\n\nPortfolio context:\n{context}"
        )

    @staticmethod
    def _messages(system_prompt: str, prompt: str, history: list[dict[str, str]]) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": system_prompt}]
        for message in history[-12:]:
            role = message.get("role")
            content = message.get("content")
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def _openai(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        prompt: str,
        history: list[dict[str, str]],
    ) -> str:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": self._messages(system_prompt, prompt, history),
                "temperature": 0.3,
            },
        )
        response.raise_for_status()
        payload = response.json()
        try:
            return str(payload["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise self._invalid_provider_payload("openai", payload) from exc

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
        for message in history[-12:]:
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
                "generationConfig": {"temperature": 0.3},
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
                "max_tokens": 1400,
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
            details={"provider": provider, "body": str(payload)[:500]},
        )

    @staticmethod
    def _gemini_model_resource(model: str) -> str:
        normalized = model.strip().removeprefix("models/")
        return f"models/{normalized}"
