from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class CopilotMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)


class CopilotChatRequest(BaseModel):
    provider: Literal["openai", "gemini", "claude"]
    api_key: str = Field(min_length=8, max_length=2000)
    prompt: str = Field(min_length=1, max_length=12000)
    context: dict[str, Any] = Field(default_factory=dict)
    history: list[CopilotMessage] = Field(default_factory=list, max_length=30)
    model: Optional[str] = Field(default=None, max_length=128)


class CopilotChatResponse(BaseModel):
    success: bool = True
    provider: str
    model: str
    answer: str
    fallback_used: bool = False
