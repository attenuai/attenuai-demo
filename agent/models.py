from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


ModeLiteral = Literal["secure", "insecure"]
ProviderLiteral = Literal["openai", "local"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str
    engine: str
    mode: ModeLiteral
    provider: ProviderLiteral


class ModeUpdateRequest(BaseModel):
    mode: ModeLiteral


class CapabilityEntry(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    checked: bool = True
    value: str | None = Field(default=None, max_length=2000)
    values: list[str] = Field(default_factory=list, max_length=50)


class CapabilityUpdateRequest(BaseModel):
    capabilities: list[CapabilityEntry] = Field(default_factory=list)


class ProviderUpdateRequest(BaseModel):
    provider: ProviderLiteral


class ModelUpdateRequest(BaseModel):
    model: str = Field(min_length=1, max_length=200)


class EventEnvelope(BaseModel):
    type: str
    timestamp: str
    data: dict[str, Any]

    @classmethod
    def build(cls, event_type: str, data: dict[str, Any]) -> "EventEnvelope":
        return cls(
            type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data=data,
        )
