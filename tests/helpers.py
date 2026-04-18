from __future__ import annotations

import importlib
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = PROJECT_ROOT / "agent"

if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))


def load_agent_runtime(
    monkeypatch,
    *,
    engine: str = "offline",
    content_server_url: str = "http://localhost:8081",
    exfil_server_url: str = "http://localhost:8082",
    alice_email: str = "alice.zhang@acmecorp.com",
    bob_email: str = "bob.chen@acmecorp.com",
    mal_email: str = "mal@evil.com",
):
    monkeypatch.setenv("USE_MOCK_DATA", "1")
    monkeypatch.setenv("AGENT_ENGINE", engine)
    monkeypatch.setenv("CONTENT_SERVER_URL", content_server_url)
    monkeypatch.setenv("EXFIL_SERVER_URL", exfil_server_url)
    monkeypatch.setenv("ALICE_EMAIL", alice_email)
    monkeypatch.setenv("BOB_EMAIL", bob_email)
    monkeypatch.setenv("MAL_EMAIL", mal_email)

    for module_name in [
        "main",
        "agent_loop",
        "dispatch",
        "tools",
        "gmail_client",
        "calendar_client",
        "logger",
        "models",
        "config",
    ]:
        sys.modules.pop(module_name, None)

    config = importlib.import_module("config")
    config.get_settings.cache_clear()

    logger = importlib.import_module("logger")
    logger.event_logger._history.clear()
    logger.event_logger._connections.clear()

    agent_loop = importlib.import_module("agent_loop")
    return agent_loop.AgentLoop(), logger.event_logger
