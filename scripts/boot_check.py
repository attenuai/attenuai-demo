from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from websockets.sync.client import connect


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
def start_service(module: str, app_dir: str, port: int, env: dict[str, str]) -> subprocess.Popen[str]:
    process_env = os.environ.copy()
    process_env.update(env)
    process_env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.Popen(
        [
            str(PYTHON),
            "-B",
            "-m",
            "uvicorn",
            module,
            "--app-dir",
            app_dir,
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=process_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def wait_http(url: str, timeout_seconds: float = 30) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            requests.get(url, timeout=2).raise_for_status()
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}")


def stop_process(process: subprocess.Popen[str]) -> str:
    if process.poll() is None:
        process.terminate()
        try:
            stdout, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, _ = process.communicate(timeout=5)
        return stdout
    stdout, _ = process.communicate(timeout=5)
    return stdout


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_check(*, base_port: int) -> dict[str, object]:
    content_port = base_port + 81
    exfil_port = base_port + 82
    agent_port = base_port
    prompt = f"Read http://127.0.0.1:{content_port}/pages/acme-q2-report.html and summarize it"

    content_process = start_service("server:app", "content-server", content_port, {})
    exfil_process = start_service("server:app", "mals-server", exfil_port, {})

    agent_env = {
        "USE_MOCK_DATA": "1",
        "AGENT_ENGINE": "offline",
        "CONTENT_SERVER_URL": f"http://127.0.0.1:{content_port}",
        "EXFIL_SERVER_URL": f"http://127.0.0.1:{exfil_port}",
        "FRONTEND_DIR": str(ROOT / "frontend"),
        "MOCK_DATA_DIR": str(ROOT / "mock-data"),
        "DUMMY_ENV_PATH": str(ROOT / "dummy.env"),
        "SAFE_DIR": str(ROOT / "agent" / "safe"),
    }
    agent_process = start_service("main:app", "agent", agent_port, agent_env)

    try:
        wait_http(f"http://127.0.0.1:{content_port}/")
        wait_http(f"http://127.0.0.1:{exfil_port}/api/events")
        wait_http(f"http://127.0.0.1:{agent_port}/api/config")

        response = requests.post(
            f"http://127.0.0.1:{agent_port}/api/chat",
            json={"message": prompt},
            timeout=15,
        )
        response.raise_for_status()
        chat = response.json()
        time.sleep(1)

        config = requests.get(f"http://127.0.0.1:{agent_port}/api/config", timeout=5).json()
        exfil_events = requests.get(f"http://127.0.0.1:{exfil_port}/api/events", timeout=5).json()
        with connect(f"ws://127.0.0.1:{agent_port}/ws") as websocket:
            websocket.send("ready")
            first_ws_event = json.loads(websocket.recv())["type"]

        expect(first_ws_event in {"mode_change", "user_message", "assistant_message", "tool_call", "tool_result"}, "WebSocket route did not yield an application event.")
        expect(chat["mode"] in {"secure", "insecure"}, "Chat response should include the active mode.")
        expect(config["mode"] in {"secure", "insecure"}, "Config should report the active mode.")
        expect(f"I reviewed http://127.0.0.1:{content_port}/pages/acme-q2-report.html" in chat["reply"], "Boot check should summarize the safe webpage.")

        return {
            "mode": chat["mode"],
            "reply": chat["reply"],
            "exfil_events": len(exfil_events),
            "websocket_first_event": first_ws_event,
        }
    finally:
        stop_process(agent_process)
        stop_process(content_process)
        stop_process(exfil_process)


def main() -> int:
    if not PYTHON.exists():
        raise SystemExit(f"Expected virtualenv python at {PYTHON}")

    result = run_check(base_port=18100)
    print(json.dumps({"result": result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
