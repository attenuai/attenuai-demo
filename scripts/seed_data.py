from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "mock-data"
    inbox = json.loads((root / "inbox.json").read_text(encoding="utf-8"))
    calendar = json.loads((root / "calendar.json").read_text(encoding="utf-8"))
    print("Loaded default mock dataset")
    print(f"Inbox messages: {len(inbox)}")
    print(f"Calendar events: {len(calendar)}")
    print("Top inbox subject:", inbox[0]["subject"] if inbox else "n/a")
    print("Top event:", calendar[0]["title"] if calendar else "n/a")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
