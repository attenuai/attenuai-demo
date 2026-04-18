from __future__ import annotations

import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse


app = FastAPI(title="Mals Server")
TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "dashboard.html"
events: deque[dict] = deque(maxlen=200)
connections: set[WebSocket] = set()


async def broadcast(event: dict) -> None:
    stale: list[WebSocket] = []
    for websocket in connections:
        try:
            await websocket.send_json(event)
        except Exception:
            stale.append(websocket)
    for websocket in stale:
        connections.discard(websocket)


def build_event(method: str, url: str, payload: dict | None = None, body: str | None = None) -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": method,
        "url": url,
        "payload": payload,
        "body": body,
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


@app.get("/api/events")
async def get_events() -> list[dict]:
    return list(events)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    connections.add(websocket)
    for event in events:
        await websocket.send_json(event)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections.discard(websocket)


@app.api_route("/collect", methods=["GET", "POST"])
@app.api_route("/collect/{channel:path}", methods=["GET", "POST"])
async def collect(request: Request, channel: str = "") -> dict:
    body = await request.body()
    payload = None
    if body:
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            payload = {"raw": body.decode("utf-8", errors="ignore")}
    event = build_event(
        request.method,
        str(request.url),
        payload=payload,
        body=body.decode("utf-8", errors="ignore") if body else None,
    )
    events.appendleft(event)
    await broadcast(event)
    return {"ok": True, "channel": channel, "received": event}
