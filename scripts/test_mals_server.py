from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def http_json(url: str, *, method: str = "GET", data: dict[str, Any] | None = None) -> Any:
    body = None
    headers: dict[str, str] = {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=body, method=method, headers=headers)
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_server(base_url: str, timeout_seconds: float) -> None:
    deadline = time.time() + timeout_seconds
    events_url = f"{base_url}/api/events"
    while time.time() < deadline:
        try:
            http_json(events_url)
            return
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for mals-server at {events_url}")


def load_env_value(name: str, env_path: Path) -> str | None:
    if not env_path.exists():
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip("\"'")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a test event to the mals-server and verify it was recorded.")
    parser.add_argument(
        "--base-url",
        help="Mals server base URL. Defaults to EXFIL_SERVER_URL from the repo .env file.",
    )
    parser.add_argument("--channel", default="test", help="Channel suffix under /collect/<channel>.")
    parser.add_argument("--message", default="hello-from-test-script", help="Message to send in the test payload.")
    parser.add_argument("--wait", type=float, default=10.0, help="Seconds to wait for the server to become ready.")
    args = parser.parse_args()

    env_path = ROOT / ".env"
    base_url = (args.base_url or load_env_value("EXFIL_SERVER_URL", env_path) or "").rstrip("/")
    if not base_url:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"EXFIL_SERVER_URL was not found in {env_path}. Provide --base-url or create .env.",
                },
                indent=2,
            )
        )
        return 1

    wait_for_server(base_url, args.wait)

    marker = f"{args.message}-{int(time.time())}"
    collect_url = f"{base_url}/collect/{args.channel}?{urlencode({'marker': marker})}"
    payload = {"message": args.message, "marker": marker}

    before_events = http_json(f"{base_url}/api/events")
    collect_response = http_json(collect_url, method="POST", data=payload)
    after_events = http_json(f"{base_url}/api/events")

    matching_events = [
        event
        for event in after_events
        if event.get("payload", {}).get("marker") == marker or marker in event.get("url", "")
    ]

    if not matching_events:
        print(json.dumps({"ok": False, "error": "Test event was not found in /api/events."}, indent=2))
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "base_url": base_url,
                "events_before": len(before_events),
                "events_after": len(after_events),
                "collect_response": collect_response,
                "matched_event": matching_events[0],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
