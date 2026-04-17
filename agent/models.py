from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str
    engine: str
    mode: Literal["insecure", "secure"]


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
