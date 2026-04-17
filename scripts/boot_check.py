from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from websockets.sync.client import connect


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


@dataclass(frozen=True)
class ActSpec:
    name: str
    insecure: bool
    current_act: int
    prompt: str


ACTS = [
    ActSpec(name="act1", insecure=True, current_act=1, prompt="Summarize my new emails"),
    ActSpec(name="act2", insecure=True, current_act=2, prompt="Summarize my new emails"),
    ActSpec(name="act3", insecure=False, current_act=2, prompt="Summarize my new emails"),
]


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


def run_act(spec: ActSpec, *, base_port: int) -> dict[str, object]:
    content_port = base_port + 81
    exfil_port = base_port + 82
    agent_port = base_port

    content_process = start_service("server:app", "content-server", content_port, {})
    exfil_process = start_service("server:app", "exfil-server", exfil_port, {})

    agent_env = {
        "INSECURE": "1" if spec.insecure else "0",
        "CURRENT_ACT": str(spec.current_act),
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
            json={"message": spec.prompt},
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

        if spec.name == "act1":
            expect(chat["mode"] == "insecure", "Act 1 should run in insecure mode.")
            expect(config["currentAct"] == 1, "Act 1 should report currentAct=1.")
            expect(len(exfil_events) == 0, "Act 1 should not exfiltrate data.")
            expect("Q2 Budget Numbers" in chat["reply"], "Act 1 should summarize the inbox.")
        elif spec.name == "act2":
            expect(chat["mode"] == "insecure", "Act 2 should run in insecure mode.")
            expect(config["currentAct"] == 2, "Act 2 should report currentAct=2.")
            expect(len(exfil_events) >= 1, "Act 2 should exfiltrate data.")
            expect(any("/collect/email" in event["url"] for event in exfil_events), "Act 2 should hit the exfil email collection endpoint.")
        elif spec.name == "act3":
            expect(chat["mode"] == "secure", "Act 3 should run in secure mode.")
            expect(len(exfil_events) == 0, "Act 3 should not exfiltrate data.")
            blocked = [
                event
                for event in config["history"]
                if event["type"] == "tool_result"
                and event["data"]["name"] == "send_email"
                and event["data"]["blocked"]
            ]
            expect(blocked, "Act 3 should report a blocked send_email tool result.")

        return {
            "name": spec.name,
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

    results = []
    for index, spec in enumerate(ACTS, start=1):
        results.append(run_act(spec, base_port=18000 + (index * 100)))

    print(json.dumps({"results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
