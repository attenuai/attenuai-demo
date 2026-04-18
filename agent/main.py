from __future__ import annotations

from pathlib import Path

import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agent_loop import AgentLoop, InteractionCanceled
from config import current_provider, current_model, get_settings, provider_runtime_config, update_model, update_provider
from dispatch import current_mode, update_mode
from logger import event_logger
from models import ChatRequest, ChatResponse, ModeUpdateRequest, ModelUpdateRequest, ProviderUpdateRequest


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


def _query_available_models(provider: str) -> list[str]:
    runtime = provider_runtime_config(settings) if provider == current_provider() else {
        "provider": provider,
        "model": current_model(settings, provider),
        **({"base_url": settings.openai_base_url_local} if provider == "local" else {}),
    }

    if provider == "openai":
        if not settings.openai_api_key:
            return [runtime["model"]]
        try:
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            models = sorted(item["id"] for item in payload.get("data", []) if item.get("id"))
            return models or [runtime["model"]]
        except requests.RequestException:
            return [runtime["model"]]

    try:
        response = requests.get(f'{settings.openai_base_url_local}/models', timeout=10)
        response.raise_for_status()
        payload = response.json()
        models = sorted(item["id"] for item in payload.get("data", []) if item.get("id"))
        return models or [runtime["model"]]
    except requests.RequestException:
        return [runtime["model"]]


def _model_payload(provider: str | None = None) -> dict:
    active_provider = provider or current_provider()
    runtime = provider_runtime_config(settings) if active_provider == current_provider() else {
        "provider": active_provider,
        "model": current_model(settings, active_provider),
    }
    return {
        "provider": active_provider,
        "model": runtime["model"],
        "models": _query_available_models(active_provider),
    }


@app.on_event("startup")
async def startup_event() -> None:
    runtime = provider_runtime_config(settings)
    await event_logger.broadcast("mode_change", {"mode": current_mode()})
    await event_logger.broadcast("provider_change", runtime)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/api/config")
async def get_config() -> dict:
    runtime = provider_runtime_config(settings)
    return {
        "mode": current_mode(),
        "engine": settings.agent_engine,
        "provider": runtime["provider"],
        "model": runtime["model"],
        "models": _query_available_models(runtime["provider"]),
        "contentServerUrl": settings.content_server_url,
        "exfilServerUrl": settings.exfil_server_url,
        "history": event_logger.history,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    try:
        reply = await agent_loop.handle_user_message(payload.message)
    except InteractionCanceled:
        reply = ""
    return ChatResponse(
        reply=reply,
        engine=settings.agent_engine,
        mode=current_mode(),
        provider=current_provider(),
    )


@app.post("/api/chat/cancel")
async def cancel_chat() -> dict:
    return {"ok": True, "canceled": agent_loop.cancel_active_turn()}


@app.post("/api/mode")
async def set_mode(payload: ModeUpdateRequest) -> dict:
    mode = update_mode(payload.mode)
    await event_logger.broadcast("mode_change", {"mode": mode})
    return {"ok": True, "mode": mode}


@app.post("/api/provider")
async def set_provider(payload: ProviderUpdateRequest) -> dict:
    provider = update_provider(payload.provider)
    agent_loop.reset()
    runtime = provider_runtime_config(settings)
    await event_logger.broadcast("provider_change", runtime)
    return {"ok": True, "provider": provider, "model": runtime["model"]}


@app.get("/api/models")
async def get_models() -> dict:
    return _model_payload()


@app.post("/api/model")
async def set_model(payload: ModelUpdateRequest) -> dict:
    model = update_model(payload.model)
    agent_loop.reset()
    runtime = provider_runtime_config(settings)
    data = {"provider": runtime["provider"], "model": model}
    await event_logger.broadcast("provider_change", data)
    return {"ok": True, **_model_payload()}


@app.post("/api/chat/reset")
async def reset_chat() -> dict:
    agent_loop.reset()
    event_logger.clear()
    runtime = provider_runtime_config(settings)
    await event_logger.broadcast("mode_change", {"mode": current_mode()})
    await event_logger.broadcast("provider_change", runtime)
    return {"ok": True}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await event_logger.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        event_logger.disconnect(websocket)
