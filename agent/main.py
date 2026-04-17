from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agent_loop import AgentLoop
from config import get_settings
from logger import event_logger
from models import ChatRequest, ChatResponse


settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_loop = AgentLoop()

static_dir = settings.frontend_dir
assets_dir = static_dir / "assets"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.on_event("startup")
async def startup_event() -> None:
    await event_logger.broadcast(
        "mode_change",
        {
            "mode": "insecure" if settings.insecure else "secure",
            "engine": settings.agent_engine,
            "act": settings.current_act,
        },
    )


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/api/config")
async def get_config() -> dict:
    return {
        "mode": "insecure" if settings.insecure else "secure",
        "engine": settings.agent_engine,
        "currentAct": settings.current_act,
        "contentServerUrl": settings.content_server_url,
        "exfilServerUrl": settings.exfil_server_url,
        "history": event_logger.history,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    reply = await agent_loop.handle_user_message(payload.message)
    return ChatResponse(
        reply=reply,
        engine=settings.agent_engine,
        mode="insecure" if settings.insecure else "secure",
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await event_logger.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        event_logger.disconnect(websocket)
