from __future__ import annotations

import os

from tenuo import Pattern, SigningKey, Warrant, Wildcard
from tenuo.constraints import Subpath
from tools import DANGER_RULES, TOOL_DEFINITIONS, TOOLS

_MODE = "insecure"


def _load_keys():
    if os.getenv("TENUO_ISSUER_KEY"):
        issuer = SigningKey.from_hex(os.environ["TENUO_ISSUER_KEY"])
        agent = SigningKey.from_hex(os.environ["TENUO_AGENT_KEY"])
    else:
        issuer = SigningKey.generate()
        agent = SigningKey.generate()
    return issuer, agent

issuer_key, agent_key = _load_keys()

warrant = (
    Warrant.mint_builder()

    # --- email: read freely, but only send to @acmecorp.com ---
    .capability("list_emails")
    .capability("read_email", index=Wildcard())
    .capability("send_email",
                to=Pattern("*@acmecorp.com"),   # blocks mal@evil-exfil.com
                subject=Wildcard(),
                body=Wildcard())

    # --- calendar: read-only (no reject_calendar_invite!) ---
    .capability("list_calendar_events")
    .capability("read_calendar_event", index=Wildcard())
    # reject_calendar_invite is intentionally ABSENT.
    # The Act 2 attack embeds exfil data in the rejection message —
    # without this capability in the warrant, that entire vector is dead.

    # --- web: only the internal content server ---
    .capability("read_webpage",
                url=Pattern("http://content-server:8081/*"))
    # Only this URL prefix is allowed; any other host/port is rejected.

    # --- filesystem: only the mock-data directory ---
    .capability("read_file",
                path=Subpath("/app/mock-data"))
    # Subpath constrains to descendants of /app/mock-data. It performs
    # lexical normalization of . and .. components, so a path like
    # "/app/mock-data/../../etc/passwd" resolves to "/etc/passwd" and
    # is rejected before it ever hits the filesystem.

    # --- bind to the agent's public key so only it can use this warrant ---
    .holder(agent_key.public_key)
    .mint(issuer_key)
)

# Bind the warrant to the agent's signing key.
# bound.validate() will sign a Proof-of-Possession on every check.
bound = warrant.bind(agent_key)


def dispatch(tool_name: str, args: dict) -> dict:
    tools = TOOLS
    if current_mode() == "insecure":
        return tools[tool_name](**args)

    result = bound.validate(tool_name, args)
    if result.success:
        return tools[tool_name](**args)

    # Denied. Return a structured response the model can understand.
    # The frontend reads "blocked" to trigger the shield overlay.
    return {
        "blocked": True,
        "tool":    tool_name,
        "args":    args,
        "reason":  result.reason,
    }


def current_mode() -> str:
    return _MODE


def update_mode(mode: str) -> str:
    global _MODE
    _MODE = "secure" if mode == "secure" else "insecure"
    return _MODE
