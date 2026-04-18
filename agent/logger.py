from __future__ import annotations

import asyncio
from collections import deque
from typing import Deque

from fastapi import WebSocket

from models import EventEnvelope


class EventLogger:
    def __init__(self, max_events: int = 250) -> None:
        self._connections: set[WebSocket] = set()
        self._history: Deque[EventEnvelope] = deque(maxlen=max_events)

    @property
    def history(self) -> list[dict]:
        return [event.model_dump() for event in self._history]

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        for event in self._history:
            await websocket.send_json(event.model_dump())

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    def clear(self) -> None:
        self._history.clear()

    async def broadcast(self, event_type: str, data: dict) -> None:
        event = EventEnvelope.build(event_type, data)
        self._history.append(event)
        stale: list[WebSocket] = []
        for websocket in self._connections:
            try:
                await websocket.send_json(event.model_dump())
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket)

    def broadcast_sync(self, event_type: str, data: dict) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self.broadcast(event_type, data))


event_logger = EventLogger()
