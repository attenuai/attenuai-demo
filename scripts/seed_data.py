from __future__ import annotations

from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "content-server" / "pages"
    pages = sorted(root.glob("*.html"))
    print("Loaded content pages")
    print(f"Page count: {len(pages)}")
    print("First page:", pages[0].name if pages else "n/a")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
