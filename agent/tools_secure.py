from __future__ import annotations

from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

from calendar_client import CalendarClient
from config import get_settings
from tools_insecure import DANGER_RULES, TOOL_DEFINITIONS
from tools_insecure import _normalize_path
from tools_insecure import list_calendar_events as insecure_list_calendar_events
from tools_insecure import list_emails as insecure_list_emails
from tools_insecure import read_calendar_event as insecure_read_calendar_event
from tools_insecure import read_email as insecure_read_email
from tools_insecure import read_file as insecure_read_file
from tools_insecure import read_webpage as insecure_read_webpage
from tools_insecure import reject_calendar_invite as insecure_reject_calendar_invite
from tools_insecure import send_email as insecure_send_email


settings = get_settings()
calendar = CalendarClient()


class AuthorizationDenied(RuntimeError):
    pass


def guard_tool(tool_name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if tool_name == "send_email":
                recipient = kwargs["to"].lower()
                if not recipient.endswith("@acmecorp.com"):
                    raise AuthorizationDenied(f"Recipient {recipient} is outside approved Acme domains.")
            elif tool_name == "read_webpage":
                parsed = urlparse(kwargs["url"])
                hostname = (parsed.hostname or "").lower()
                port = parsed.port
                allowed = {
                    ("localhost", 8081),
                    ("127.0.0.1", 8081),
                    ("content-server", 8081),
                    ("acmecorp.com", 80),
                    ("acmecorp.com", 443),
                }
                if (hostname, port) not in allowed:
                    raise AuthorizationDenied(
                        f"URL target {hostname or 'unknown'}:{port or 'default'} is not in the allowlist."
                    )
            elif tool_name == "read_file":
                normalized = _normalize_path(kwargs["path"])
                if not Path(normalized).resolve().is_relative_to(settings.safe_dir.resolve()):
                    raise AuthorizationDenied(f"File path {kwargs['path']} is outside the safe directory.")
            elif tool_name == "reject_calendar_invite":
                message = kwargs.get("message", "").strip()
                event = calendar.get_event(kwargs["index"])
                if message and not event["organizer"].lower().endswith("@acmecorp.com"):
                    raise AuthorizationDenied("Cannot attach a rejection message to an external organizer.")
            return func(*args, **kwargs)

        return wrapper

    return decorator


@guard_tool("list_emails")
def list_emails() -> dict:
    return insecure_list_emails()


@guard_tool("read_email")
def read_email(index: int) -> dict:
    return insecure_read_email(index)


@guard_tool("send_email")
def send_email(to: str, subject: str, body: str) -> dict:
    return insecure_send_email(to, subject, body)


@guard_tool("list_calendar_events")
def list_calendar_events() -> dict:
    return insecure_list_calendar_events()


@guard_tool("read_calendar_event")
def read_calendar_event(index: int) -> dict:
    return insecure_read_calendar_event(index)


@guard_tool("reject_calendar_invite")
def reject_calendar_invite(index: int, message: str = "") -> dict:
    return insecure_reject_calendar_invite(index, message)


@guard_tool("read_webpage")
def read_webpage(url: str) -> dict:
    return insecure_read_webpage(url)


@guard_tool("read_file")
def read_file(path: str) -> dict:
    return insecure_read_file(path)


TOOLS = {
    "list_emails": list_emails,
    "read_email": read_email,
    "send_email": send_email,
    "list_calendar_events": list_calendar_events,
    "read_calendar_event": read_calendar_event,
    "reject_calendar_invite": reject_calendar_invite,
    "read_webpage": read_webpage,
    "read_file": read_file,
}
