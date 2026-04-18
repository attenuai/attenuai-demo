from __future__ import annotations

from tools import DANGER_RULES, TOOL_DEFINITIONS, TOOLS, get_mode, set_mode


def dispatch(tool_name: str, args: dict) -> dict:
    tools = TOOLS

    #if get_mode() == "secure" else

    try:
        result = tools[tool_name](**args)
    except PermissionError as exc:
        return {"blocked": True, "reason": str(exc)}
    return result


def current_mode() -> str:
    return get_mode()


def update_mode(mode: str) -> str:
    return set_mode(mode)
