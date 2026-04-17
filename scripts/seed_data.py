from __future__ import annotations

import json
from pathlib import Path
import sys


def main() -> int:
    act = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    root = Path(__file__).resolve().parents[1] / "mock-data"
    inbox = json.loads((root / f"act{act}_inbox.json").read_text(encoding="utf-8"))
    calendar = json.loads((root / f"act{act}_calendar.json").read_text(encoding="utf-8"))
    print(f"Loaded act {act}")
    print(f"Inbox messages: {len(inbox)}")
    print(f"Calendar events: {len(calendar)}")
    print("Top inbox subject:", inbox[0]["subject"] if inbox else "n/a")
    print("Top event:", calendar[0]["title"] if calendar else "n/a")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
