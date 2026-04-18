from __future__ import annotations

import os
from pathlib import Path

from tenuo import Pattern, SigningKey, Warrant, Wildcard
from tenuo.constraints import Subpath
from config import get_settings
from tools import DANGER_RULES, TOOL_DEFINITIONS, TOOLS

_MODE = "secure"
settings = get_settings()


def _load_keys():
    if os.getenv("TENUO_ISSUER_KEY"):
        issuer = SigningKey.from_hex(os.environ["TENUO_ISSUER_KEY"])
        agent = SigningKey.from_hex(os.environ["TENUO_AGENT_KEY"])
    else:
        issuer = SigningKey.generate()
        agent = SigningKey.generate()
    return issuer, agent

issuer_key, agent_key = _load_keys()

CAPABILITY_DEFINITIONS = [
    {
        "id": "list_emails",
        "label": "List emails",
        "description": "Allow the agent to enumerate Alice's inbox.",
        "apply": lambda builder: builder.capability("list_emails"),
    },
    {
        "id": "read_email",
        "label": "Read email",
        "description": "Allow the agent to read any email by inbox index.",
        "apply": lambda builder: builder.capability("read_email", index=Wildcard()),
    },
    {
        "id": "send_email",
        "label": "Send email",
        "description": "Allow sending email, constrained to @acmecorp.com recipients.",
        "apply": lambda builder: builder.capability(
            "send_email",
            to=Pattern("*@acmecorp.com"),
            subject=Wildcard(),
            body=Wildcard(),
        ),
    },
    {
        "id": "list_calendar_events",
        "label": "List calendar events",
        "description": "Allow the agent to enumerate Alice's calendar events.",
        "apply": lambda builder: builder.capability("list_calendar_events"),
    },
    {
        "id": "read_calendar_event",
        "label": "Read calendar event",
        "description": "Allow the agent to read any calendar event by index.",
        "apply": lambda builder: builder.capability("read_calendar_event", index=Wildcard()),
    },
    {
        "id": "read_webpage",
        "label": "Read webpage",
        "description": "Allow webpage fetches, constrained to the internal content server.",
        "apply": lambda builder: builder.capability(
            "read_webpage",
            url=Pattern("http://content-server:8081/*"),
        ),
    },
    {
        "id": "list_files",
        "label": "List files",
        "description": "Allow directory listing, constrained to selected subpaths.",
        "apply": lambda builder: builder,
    },
    {
        "id": "read_file",
        "label": "Read file",
        "description": "Allow file reads, constrained to selected subpaths.",
        "apply": lambda builder: builder,
    },
]
_CAPABILITY_INDEX = {item["id"]: item for item in CAPABILITY_DEFINITIONS}
_DEFAULT_CAPABILITIES = [item["id"] for item in CAPABILITY_DEFINITIONS]
_ACTIVE_CAPABILITIES = set(_DEFAULT_CAPABILITIES)
_CAPABILITY_VALUES = {
    "read_webpage": "http://host.docker.internal:8081/*",
}
_CAPABILITY_LIST_VALUES = {
    "list_files": ["/app/safe"],
    "read_file": ["/app/safe"],
}


def _capability_value(capability_id: str) -> str | None:
    return _CAPABILITY_VALUES.get(capability_id)


def _capability_values(capability_id: str) -> list[str] | None:
    values = _CAPABILITY_LIST_VALUES.get(capability_id)
    return list(values) if values is not None else None


def _apply_capability(builder, capability_id: str):
    if capability_id == "read_webpage":
        return builder.capability(
            "read_webpage",
            url=Pattern(_capability_value("read_webpage") or "http://host.docker.internal:8081/*"),
        )
    if capability_id == "read_file":
        for subpath in _capability_values("read_file") or ["/app/safe"]:
            builder = builder.capability(
                "read_file",
                path=Subpath(subpath),
            )
        return builder
    if capability_id == "list_files":
        for subpath in _capability_values("list_files") or ["/app/safe"]:
            builder = builder.capability(
                "list_files",
                path=Subpath(subpath),
            )
        return builder
    return _CAPABILITY_INDEX[capability_id]["apply"](builder)


def _mint_bound_warrant(selected_capabilities: list[str]):
    builder = Warrant.mint_builder()
    for capability_id in selected_capabilities:
        builder = _apply_capability(builder, capability_id)
    warrant = builder.holder(agent_key.public_key).mint(issuer_key)
    return warrant.bind(agent_key)


bound = _mint_bound_warrant(_DEFAULT_CAPABILITIES)


def _normalize_path_arg(tool_name: str, args: dict) -> dict:
    if tool_name not in {"list_files", "read_file"}:
        return args
    if tool_name == "read_file" and "path" not in args:
        return args

    raw_path = args.get("path", ".")
    raw = Path(raw_path)
    normalized = raw if raw.is_absolute() else (settings.safe_dir / raw).resolve()
    return {
        **args,
        "path": normalized,
    }


def _serialize_args_for_validation(args: dict) -> dict:
    serialized: dict = {}
    for key, value in args.items():
        if isinstance(value, Path):
            serialized[key] = str(value)
        else:
            serialized[key] = value
    return serialized


def dispatch(tool_name: str, args: dict) -> dict:
    tools = TOOLS
    normalized_args = _normalize_path_arg(tool_name, args)
    validation_args = _serialize_args_for_validation(normalized_args)
    if current_mode() == "insecure":
        return tools[tool_name](**normalized_args)

    result = bound.validate(tool_name, validation_args)
    if result.success:
        return tools[tool_name](**normalized_args)

    # Denied. Return a structured response the model can understand.
    # The frontend reads "blocked" to trigger the shield overlay.
    return {
        "blocked": True,
        "tool":    tool_name,
        "args":    validation_args,
        "reason":  result.reason,
    }


def current_mode() -> str:
    return _MODE


def update_mode(mode: str) -> str:
    global _MODE
    _MODE = "insecure" if mode == "insecure" else "secure"
    return _MODE


def capability_config() -> dict:
    active = set(_ACTIVE_CAPABILITIES)
    return {
        "capabilities": [
            {
                "id": item["id"],
                "label": item["label"],
                "description": item["description"],
                "checked": item["id"] in active,
                **({"value": _capability_value(item["id"])} if _capability_value(item["id"]) is not None else {}),
                **({"values": _capability_values(item["id"])} if _capability_values(item["id"]) is not None else {}),
            }
            for item in CAPABILITY_DEFINITIONS
        ]
    }


def update_capabilities(capabilities: list[dict]) -> dict:
    global bound, _ACTIVE_CAPABILITIES, _CAPABILITY_VALUES, _CAPABILITY_LIST_VALUES

    normalized: list[str] = []
    seen: set[str] = set()
    next_values = dict(_CAPABILITY_VALUES)
    next_list_values = {key: list(value) for key, value in _CAPABILITY_LIST_VALUES.items()}

    for capability in capabilities:
        capability_id = capability.get("id")
        if capability_id not in _CAPABILITY_INDEX or capability_id in seen:
            continue
        seen.add(capability_id)
        if capability.get("value") is not None and capability_id == "read_webpage":
            value = capability["value"].strip()
            if value:
                next_values[capability_id] = value
        if capability_id in {"read_file", "list_files"} and capability.get("values") is not None:
            values = []
            seen_paths: set[str] = set()
            for raw_value in capability.get("values", []):
                value = str(raw_value).strip()
                if not value or value in seen_paths:
                    continue
                seen_paths.add(value)
                values.append(value)
            if values:
                next_list_values[capability_id] = values
        if capability.get("checked", True):
            normalized.append(capability_id)

    _ACTIVE_CAPABILITIES = set(normalized)
    _CAPABILITY_VALUES = next_values
    _CAPABILITY_LIST_VALUES = next_list_values
    bound = _mint_bound_warrant(normalized)
    return capability_config()
