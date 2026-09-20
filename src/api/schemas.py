from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class APIError(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: APIError


class HealthResponse(BaseModel):
    success: bool = True
    status: str = "ok"
    service: str
    environment: str
    database: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReadinessResponse(BaseModel):
    success: bool = True
    status: str = "ready"
    service: str
    database: str
    migration: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class VersionResponse(BaseModel):
    success: bool = True
    service: str
    version: str
    api_prefix: str
    environment: str
