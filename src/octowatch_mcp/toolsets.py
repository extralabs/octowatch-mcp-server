"""Toolset filtering for OCTOWATCH_TOOLSETS (GitHub MCP–style)."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("octowatch_mcp")

CORE_TOOLS = frozenset(
    {
        "octowatch_whoami",
        "list_users_groups",
        "list_risks",
        "list_anomalies",
        "get_idle_summary",
        "get_activity_summary",
        "get_timesheet",
        "get_productivity_summary",
        "list_reports",
    }
)

CONSOLE_TOOLS = frozenset(
    {
        "get_analytics",
        "get_dashboard",
        "get_chrono",
        "get_day_structure",
        "list_monitoring",
        "search_monitoring",
        "get_activity_detail",
        "list_online",
        "list_stream_meta",
        "list_directory",
        "get_user_info",
        "get_account_readonly",
        "list_api_coverage",
    }
)

ALL_TOOLS = CORE_TOOLS | CONSOLE_TOOLS


def resolve_enabled_tools(raw: str | None = None) -> frozenset[str] | None:
    """Return enabled tool names, or None when all tools stay registered.

    ``console`` alone auto-includes ``core``.
    """
    value = (raw if raw is not None else os.environ.get("OCTOWATCH_TOOLSETS", "all")).strip()
    if not value or value.lower() == "all":
        return None

    parts = {p.strip().lower() for p in value.split(",") if p.strip()}
    unknown = parts - {"core", "console", "all"}
    if unknown:
        raise ValueError(
            f"Unknown OCTOWATCH_TOOLSETS entries: {sorted(unknown)}. "
            "Use: all | core | console | core,console"
        )
    if "all" in parts:
        return None

    enabled: set[str] = set()
    if "core" in parts or "console" in parts:
        # console alone still needs core (whoami / users / period helpers)
        enabled |= CORE_TOOLS
    if "console" in parts:
        enabled |= CONSOLE_TOOLS
    return frozenset(enabled)


def apply_toolsets(mcp, raw: str | None = None) -> frozenset[str] | None:
    """Remove tools not in the selected toolsets. Returns enabled set or None (=all).

    Uses the live registry (not only ALL_TOOLS) so newly added tools are filtered too.
    """
    enabled = resolve_enabled_tools(raw)
    registered = {t.name for t in mcp._tool_manager.list_tools()}
    if enabled is None:
        logger.info("Toolsets: all (%d tools)", len(registered))
        return None

    for name in sorted(registered - enabled):
        try:
            mcp.remove_tool(name)
        except Exception:
            logger.debug("Could not remove tool %s", name, exc_info=True)

    logger.info("Toolsets enabled: %s (%d tools)", sorted(enabled), len(enabled))
    return enabled
