"""OctoWatch MCP server — read-only tools for Claude / Cursor / ChatGPT."""

from __future__ import annotations

import json
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

from octowatch_mcp import __version__
from octowatch_mcp.client import (
    OctoWatchAPIError,
    OctoWatchClient,
    parse_datetime,
    users_filter_all,
    users_filter_for_group,
)
from octowatch_mcp.config import get_settings

mcp = MCPServer(
    "octowatch",
    version=__version__,
    website_url="https://octowatchdlp.com",
    instructions=(
        "Read-only OctoWatch DLP Cloud tools. Use for Risks, Anomalies (deviations), "
        "users/groups, activity, timesheet, productivity, and report settings. "
        "Dates are local tenant time: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS. "
        "Default period is the last day when dates are omitted. "
        "Demo tenant credentials may be active — never assume production data."
    ),
)

_client: OctoWatchClient | None = None


def _get_client() -> OctoWatchClient:
    global _client
    if _client is None:
        _client = OctoWatchClient(get_settings())
    return _client


def _dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _err(exc: BaseException) -> str:
    if isinstance(exc, OctoWatchAPIError):
        return _dumps(
            {
                "error": str(exc),
                "status_code": exc.status_code,
            }
        )
    return _dumps({"error": str(exc)})


# Tools return JSON errors over stdio instead of raising (keeps MCP session alive).
_TOOL_ERRORS = (OctoWatchAPIError, ValueError, OSError, RuntimeError, httpx.HTTPError)


def _period(date_from: str | None, date_to: str | None):
    return parse_datetime(date_from), parse_datetime(date_to)


def _filter(group_id: int | None):
    if group_id is None:
        return users_filter_all()
    return users_filter_for_group(group_id)


@mcp.tool()
def octowatch_whoami() -> str:
    """Show which OctoWatch API host and account the MCP server is using (password never returned)."""
    try:
        s = get_settings()
        client = _get_client()
        login = client.login()
        return _dumps(
            {
                "version": __version__,
                "api_base": s.api_base,
                "email": s.email,
                "is_demo": s.is_demo,
                "public_id": login.get("PublicID"),
                "token_expires_in": login.get("ExpiresIn"),
                "warning": (
                    "DEMO account — do not put production passwords in MCP config."
                    if s.is_demo
                    else None
                ),
            }
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def list_users_groups() -> str:
    """List users and groups tree (GetUsersGroups2). Type 0=root, 1=group, 2=user."""
    try:
        return _dumps(_get_client().get_users_groups())
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def list_risks(
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
    limit: int = 100,
) -> str:
    """List DLP/rule Risks for a period (POST /api/Risks/Overall2).

    Ask examples: "which Risks in the last day?", "Risks for Accounting group".
    """
    try:
        df, dt = _period(date_from, date_to)
        data = _get_client().risks(
            date_from=df,
            date_to=dt,
            users_filter=_filter(group_id),
            num_rows=max(1, min(limit, 500)),
        )
        return _dumps(data)
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def list_anomalies(
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
    limit: int = 100,
    filter_key: str | None = None,
) -> str:
    """List behavior Anomalies / deviations (POST /api/Alerts/Overall2).

    Includes idle, lateness, overtime, unusual app usage, etc.
    Ask examples: "who was idle too long?", "anomalies yesterday".
    """
    try:
        df, dt = _period(date_from, date_to)
        data = _get_client().anomalies(
            date_from=df,
            date_to=dt,
            users_filter=_filter(group_id),
            num_rows=max(1, min(limit, 500)),
            filter_key=filter_key,
        )
        return _dumps(data)
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def get_activity_summary(
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
) -> str:
    """Activity summary for apps/sites in a period (POST /api/Activity/Overall2)."""
    try:
        df, dt = _period(date_from, date_to)
        return _dumps(
            _get_client().activity(
                date_from=df,
                date_to=dt,
                users_filter=_filter(group_id),
            )
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def get_timesheet(
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
) -> str:
    """Timesheet / attendance-style summary (POST /api/TimeSheet/Overall2)."""
    try:
        df, dt = _period(date_from, date_to)
        return _dumps(
            _get_client().timesheet(
                date_from=df,
                date_to=dt,
                users_filter=_filter(group_id),
            )
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def get_productivity_summary(
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
) -> str:
    """Per-user productivity breakdown for a period (POST /api/Productivity/Overall3).

    Also useful with analytics rollup via Metrics on Analytics/Overall.
    """
    try:
        df, dt = _period(date_from, date_to)
        client = _get_client()
        filt = _filter(group_id)
        detail = client.productivity(date_from=df, date_to=dt, users_filter=filt)
        stats = client.productivity_stats(date_from=df, date_to=dt, users_filter=filt)
        analytics = client.analytics_summary(date_from=df, date_to=dt, users_filter=filt)
        return _dumps(
            {
                "productivity_detail": detail,
                "productivity_stats": stats,
                "analytics_metrics": analytics.get("Metrics") if isinstance(analytics, dict) else None,
                "top_risks": analytics.get("Risks") if isinstance(analytics, dict) else None,
            }
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def list_reports() -> str:
    """List scheduled report mailing settings and background processing tasks.

    Demo may return an empty GetReports list; processing tasks still show recent jobs.
    """
    try:
        client = _get_client()
        return _dumps(
            {
                "scheduled_reports": client.get_reports_settings(),
                "processing_tasks": client.get_processing_tasks(),
            }
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


def main() -> None:
    # Touch settings early so demo warning appears in stderr at startup.
    get_settings()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
