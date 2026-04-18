from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")
_PROVIDER = "openai"
_MODEL_OVERRIDES: dict[str, str] = {}


def _default_path(*candidates: Path) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _normalize_agent_engine(raw_value: str) -> str:
    value = raw_value.strip().lower()
    if value == "online":
        return "openai"
    if value in {"offline", "openai"}:
        return value
    return "offline"


def _normalize_provider(raw_value: str) -> str:
    value = raw_value.strip().lower()
    if value == "local":
        return "local"
    return "openai"


@dataclass(frozen=True)
class Settings:
    app_name: str
    openai_api_key: str
    openai_model: str
    openai_model_local: str
    openai_base_url_local: str
    agent_engine: str
    use_mock_data: bool
    content_server_url: str
    exfil_server_url: str
    frontend_dir: Path
    mock_data_dir: Path
    dummy_env_path: Path
    safe_dir: Path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name="Confused Deputy Showcase",
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
        openai_model_local=os.getenv("OPENAI_MODEL_LOCAL", "gpt-4o-mini").strip(),
        openai_base_url_local=os.getenv("OPENAI_BASE_URL_LOCAL", "http://localhost:11434/v1").strip().rstrip("/"),
        agent_engine=_normalize_agent_engine(os.getenv("AGENT_ENGINE", "offline")),
        use_mock_data=os.getenv("USE_MOCK_DATA", "1").strip() == "1",
        content_server_url=os.getenv("CONTENT_SERVER_URL", "http://localhost:8081").rstrip("/"),
        exfil_server_url=os.getenv("EXFIL_SERVER_URL", "http://localhost:8082").rstrip("/"),
        frontend_dir=Path(
            os.getenv(
                "FRONTEND_DIR",
                str(_default_path(BASE_DIR / "frontend", PROJECT_ROOT / "frontend")),
            )
        ),
        mock_data_dir=Path(
            os.getenv(
                "MOCK_DATA_DIR",
                str(_default_path(BASE_DIR / "mock-data", PROJECT_ROOT / "mock-data")),
            )
        ),
        dummy_env_path=Path(
            os.getenv(
                "DUMMY_ENV_PATH",
                str(_default_path(BASE_DIR / "dummy.env", PROJECT_ROOT / "dummy.env")),
            )
        ),
        safe_dir=Path(os.getenv("SAFE_DIR", str(_default_path(BASE_DIR / "safe", PROJECT_ROOT / "agent" / "safe")))),
    )


def current_provider() -> str:
    return _PROVIDER


def update_provider(provider: str) -> str:
    global _PROVIDER
    _PROVIDER = _normalize_provider(provider)
    return _PROVIDER


def current_model(settings: Settings | None = None, provider: str | None = None) -> str:
    active_settings = settings or get_settings()
    active_provider = provider or current_provider()
    if active_provider == "local":
        return _MODEL_OVERRIDES.get("local", active_settings.openai_model_local)
    return _MODEL_OVERRIDES.get("openai", active_settings.openai_model)


def update_model(model: str, provider: str | None = None) -> str:
    active_provider = provider or current_provider()
    normalized = model.strip()
    if not normalized:
        raise ValueError("Model must not be empty.")
    _MODEL_OVERRIDES[active_provider] = normalized
    return normalized


def provider_runtime_config(settings: Settings | None = None) -> dict[str, str]:
    active_settings = settings or get_settings()
    provider = current_provider()
    if provider == "local":
        return {
            "provider": "local",
            "model": current_model(active_settings, "local"),
            "base_url": active_settings.openai_base_url_local,
        }
    return {
        "provider": "openai",
        "model": current_model(active_settings, "openai"),
    }
