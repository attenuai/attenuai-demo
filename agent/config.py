from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")


def _default_path(*candidates: Path) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


@dataclass(frozen=True)
class Settings:
    app_name: str
    openai_api_key: str
    openai_model: str
    agent_engine: str
    insecure: bool
    use_mock_data: bool
    current_act: int
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
        agent_engine=os.getenv("AGENT_ENGINE", "offline").strip().lower(),
        insecure=os.getenv("INSECURE", "1").strip() == "1",
        use_mock_data=os.getenv("USE_MOCK_DATA", "1").strip() == "1",
        current_act=int(os.getenv("CURRENT_ACT", "1").strip()),
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
