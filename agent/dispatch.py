from __future__ import annotations

from config import get_settings
from tools_insecure import DANGER_RULES, TOOL_DEFINITIONS


settings = get_settings()

if settings.insecure:
    from tools_insecure import TOOLS
else:
    from tools_secure import AuthorizationDenied, TOOLS


def dispatch(tool_name: str, args: dict) -> dict:
    try:
        return TOOLS[tool_name](**args)
    except Exception as exc:
        if type(exc).__name__ == "AuthorizationDenied":
            return {
                "blocked": True,
                "tool": tool_name,
                "reason": str(exc),
            }
        raise
