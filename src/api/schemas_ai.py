from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from src.ai.safety import MAX_PROMPT_CHARACTERS

from src.api.schemas_intelligence import Citation


class CopilotMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)


class CopilotChatRequest(BaseModel):
    portfolio_id: int = Field(gt=0)
    provider: Literal["openai", "gemini", "claude", "nvidia"] = "nvidia"
    api_key: Optional[str] = Field(default=None, max_length=2000, repr=False)
    prompt: str = Field(min_length=1, max_length=MAX_PROMPT_CHARACTERS)
    task: Literal["question", "brief", "data_check"] = "question"
    history: list[CopilotMessage] = Field(default_factory=list, max_length=30)
    model: Optional[str] = Field(default=None, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)?$")

    @field_validator("prompt")
    @classmethod
    def nonblank_prompt(cls, value):
        if not value.strip():
            raise ValueError("Enter a question.")
        return value.strip()


class AIAction(BaseModel):
    label: str
    href: Literal["/risk", "/portfolios", "/market", "/regime", "/portfolio-health", "/recommendations"]


class AIDataCheck(AIAction):
    status: Literal["available", "needs_review"]
    detail: str


class AISafetyMetadata(BaseModel):
    policy_version: str
    read_only: bool = True
    output_status: Literal["evidence_checked", "local", "rejected"]
    note: str


class RetrievalMetadata(BaseModel):
    strategy: Literal["local_hash_embeddings"]
    selected_sources: list[str]
    selected_documents: int = Field(ge=0)
    available_documents: int = Field(ge=0)
    context_characters: int = Field(ge=0)
    estimated_input_tokens: int = Field(ge=0)
    external_embedding_tokens: int = Field(ge=0)


class CopilotChatResponse(BaseModel):
    success: bool = True
    provider: str
    model: str
    answer: str
    fallback_used: bool = False
    response_mode: Literal["provider", "local", "local_fallback"]
    tools_used: list[str]
    citations: list[Citation]
    data_as_of: Optional[date] = None
    provider_error: Optional[str] = None
    retrieval: Optional[RetrievalMetadata] = None
    next_action: Optional[AIAction] = None
    data_checks: list[AIDataCheck] = Field(default_factory=list)
    safety: AISafetyMetadata
    elapsed_ms: int = Field(ge=0)


class ProviderValidationRequest(BaseModel):
    provider: Literal["openai", "gemini", "claude", "nvidia"]
    api_key: Optional[str] = Field(default=None, max_length=2000, repr=False)
    model: Optional[str] = Field(default=None, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)?$")


class ProviderValidationResponse(BaseModel):
    valid: bool = True
    provider: str
    model: str


class AIProviderConfigResponse(BaseModel):
    default_provider: Literal["openai", "gemini", "claude", "nvidia"]
    managed_provider: Literal["nvidia"] = "nvidia"
    managed_provider_configured: bool
    managed_model: str


class AIReportRequest(BaseModel):
    portfolio_id: int = Field(gt=0)
    report_type: Literal[
        "Daily Report",
        "Weekly Report",
        "Monthly Report",
        "Portfolio Summary",
        "Risk Summary",
        "Regime Summary",
        "Stress Test Report",
    ]
    provider: Literal["openai", "gemini", "claude", "nvidia"] = "nvidia"
    api_key: Optional[str] = Field(default=None, max_length=2000, repr=False)
    model: Optional[str] = Field(default=None, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)?$")


class AIReportRead(BaseModel):
    id: int
    portfolio_id: int
    report_type: str
    title: str
    content: str
    provider: Optional[str] = None
    model: Optional[str] = None
    response_mode: Literal["provider", "local", "local_fallback"]
    data_as_of: Optional[date] = None
    created_at: datetime
