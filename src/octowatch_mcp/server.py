"""OctoWatch MCP server — read-only tools for Claude / Cursor / ChatGPT."""

from __future__ import annotations

import json
from typing import Any, Literal

import httpx
from mcp.server.mcpserver import MCPServer

from octowatch_mcp import __version__
from octowatch_mcp.client import (
    OctoWatchAPIError,
    OctoWatchClient,
    users_filter_all,
    users_filter_for_group,
)
from octowatch_mcp.config import get_settings
from octowatch_mcp.formatters import (
    analytics_risks_by_user,
    filter_by_alias_id,
    format_activity_top,
    format_idle_summary,
    format_productivity_rollup,
    format_timesheet,
    slim_risk_row,
    summarize_risks_page,
)
from octowatch_mcp.period import resolve_tool_period
from octowatch_mcp.report_types import label_report_types

mcp = MCPServer(
    "octowatch",
    version=__version__,
    website_url="https://octowatchdlp.com",
    instructions=(
        "Read-only OctoWatch DLP Cloud tools. "
        "Prefer period=today|yesterday|last_7_days|last_30_days, or date_from/date_to. "
        "Date-only values cover the full calendar day (date_to ends at 23:59:59). "
        "For Risks overviews use list_risks mode=summary (default). "
        "For idle duration use get_idle_summary (InactiveTime), not list_anomalies. "
        "list_anomalies is formal Alerts/deviations only. "
        "Demo credentials may be active — never assume production data."
    ),
)

_client: OctoWatchClient | None = None
RISKS_FETCH_ALL_CAP = 2000

# Tools return JSON errors over stdio instead of raising (keeps MCP session alive).
_TOOL_ERRORS = (OctoWatchAPIError, ValueError, OSError, RuntimeError, httpx.HTTPError)


def _get_client() -> OctoWatchClient:
    global _client
    if _client is None:
        _client = OctoWatchClient(get_settings())
    return _client


def _dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _err(exc: BaseException) -> str:
    if isinstance(exc, OctoWatchAPIError):
        return _dumps({"error": str(exc), "status_code": exc.status_code})
    return _dumps({"error": str(exc)})


def _period(
    period: str | None,
    date_from: str | None,
    date_to: str | None,
):
    settings = get_settings()
    return resolve_tool_period(
        period=period,
        date_from=date_from,
        date_to=date_to,
        default_days=settings.default_days,
    )


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
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
    user_id: int | None = None,
    mode: Literal["summary", "raw"] = "summary",
    offset: int = 0,
    limit: int = 100,
    fetch_all: bool = False,
    compact: bool = True,
) -> str:
    """List or summarize DLP/rule Risks for a period.

    Default mode=summary: by_user from Analytics/Overall (accurate totals),
    by_rule/by_day/sample from one Risks/Overall2 page (or fetch_all up to 2000).
    Use mode=raw for slim or full risk rows. Prefer summary for "top Risks by person".
    """
    try:
        df, dt = _period(period, date_from, date_to)
        client = _get_client()
        filt = _filter(group_id)
        page_size = max(1, min(limit, 500))

        if mode == "raw":
            data = client.risks(
                date_from=df,
                date_to=dt,
                users_filter=filt,
                offset=max(0, offset),
                num_rows=page_size,
            )
            items = filter_by_alias_id(list(data.get("List") or []), user_id)
            if compact:
                items = [slim_risk_row(r) for r in items if isinstance(r, dict)]
            return _dumps(
                {
                    "TotalRecords": data.get("TotalRecords"),
                    "StartFrom": data.get("StartFrom"),
                    "NumRecords": len(items),
                    "List": items,
                }
            )

        analytics = client.analytics_summary(date_from=df, date_to=dt, users_filter=filt)
        by_user = analytics_risks_by_user(
            analytics.get("Risks") if isinstance(analytics, dict) else None,
            user_id=user_id,
        )

        if fetch_all:
            page = client.risks_pages(
                date_from=df,
                date_to=dt,
                users_filter=filt,
                page_size=500,
                max_rows=RISKS_FETCH_ALL_CAP,
            )
            items = filter_by_alias_id(list(page.get("List") or []), user_id)
            page_meta = summarize_risks_page([r for r in items if isinstance(r, dict)])
            total = page.get("TotalRecords")
            source_detail = "Risks/Overall2 fetch_all"
            capped = page.get("capped")
        else:
            page = client.risks(
                date_from=df,
                date_to=dt,
                users_filter=filt,
                offset=max(0, offset),
                num_rows=page_size,
            )
            items = filter_by_alias_id(list(page.get("List") or []), user_id)
            page_meta = summarize_risks_page([r for r in items if isinstance(r, dict)])
            total = page.get("TotalRecords")
            source_detail = "Risks/Overall2 page"
            capped = False

        return _dumps(
            {
                "total_records": total,
                "returned_detail_rows": len(items),
                "offset": offset if not fetch_all else 0,
                "by_user": by_user,
                "by_rule": page_meta["by_rule"],
                "by_day": page_meta["by_day"],
                "sample": page_meta["sample"],
                "source": {
                    "by_user": "Analytics/Overall",
                    "detail_page": source_detail,
                    "fetch_all": fetch_all,
                    "capped_at": RISKS_FETCH_ALL_CAP if fetch_all and capped else None,
                    "page_note": (
                        None
                        if fetch_all
                        else "by_rule/by_day/sample are from the fetched page only"
                    ),
                },
            }
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def list_anomalies(
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
    user_id: int | None = None,
    offset: int = 0,
    limit: int = 100,
    filter_key: str | None = None,
    compact: bool = True,
) -> str:
    """List formal Alerts / deviations (POST /api/Alerts/Overall2).

    Lateness, overtime, unusual app-share alerts when the timetable rules fire.
    Does NOT measure idle duration — use get_idle_summary for InactiveTime.
    """
    try:
        df, dt = _period(period, date_from, date_to)
        data = _get_client().anomalies(
            date_from=df,
            date_to=dt,
            users_filter=_filter(group_id),
            offset=max(0, offset),
            num_rows=max(1, min(limit, 500)),
            filter_key=filter_key,
        )
        items = filter_by_alias_id(list(data.get("List") or []), user_id)
        if compact:
            slim_keys = (
                "ID",
                "AliasName",
                "AliasID",
                "DateTime",
                "AlertType",
                "AlertDescription",
                "StringValue",
                "DecimalValue",
                "Hidden",
            )
            items = [
                {k: r.get(k) for k in slim_keys if r.get(k) is not None}
                for r in items
                if isinstance(r, dict)
            ]
        return _dumps(
            {
                "TotalRecords": data.get("TotalRecords"),
                "NumRecords": len(items),
                "List": items,
                "note": "Formal Alerts only. For idle duration use get_idle_summary.",
            }
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def get_idle_summary(
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
    user_id: int | None = None,
    min_idle_hours: float | None = None,
) -> str:
    """Rank users by inactive (idle) time from Productivity/Overall3.

    Answers: "who was idle longest?", "idle > 3 hours". Not the Alerts API.
    """
    try:
        df, dt = _period(period, date_from, date_to)
        detail = _get_client().productivity(
            date_from=df,
            date_to=dt,
            users_filter=_filter(group_id),
        )
        return _dumps(
            format_idle_summary(
                detail,
                user_id=user_id,
                min_idle_hours=min_idle_hours,
            )
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def get_activity_summary(
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
    user_id: int | None = None,
    top_n: int = 15,
    raw: bool = False,
) -> str:
    """Top apps and sites by ActiveTime (POST /api/Activity/Overall2)."""
    try:
        df, dt = _period(period, date_from, date_to)
        data = _get_client().activity(
            date_from=df,
            date_to=dt,
            users_filter=_filter(group_id),
        )
        if raw:
            return _dumps(data)
        return _dumps(format_activity_top(data, top_n=max(1, min(top_n, 100)), user_id=user_id))
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def get_timesheet(
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
    user_id: int | None = None,
    raw: bool = False,
) -> str:
    """Timesheet / attendance summary (POST /api/TimeSheet/Overall2).

    Default: per-user days with worked_hms and expected hours from timetable profile.
    """
    try:
        df, dt = _period(period, date_from, date_to)
        data = _get_client().timesheet(
            date_from=df,
            date_to=dt,
            users_filter=_filter(group_id),
        )
        if raw:
            return _dumps(data)
        return _dumps(format_timesheet(data, user_id=user_id))
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def get_productivity_summary(
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
    user_id: int | None = None,
    raw: bool = False,
) -> str:
    """Per-user productivity rollup (Overall3 + stats + Analytics metrics)."""
    try:
        df, dt = _period(period, date_from, date_to)
        client = _get_client()
        filt = _filter(group_id)
        detail = client.productivity(date_from=df, date_to=dt, users_filter=filt)
        stats = client.productivity_stats(date_from=df, date_to=dt, users_filter=filt)
        analytics = client.analytics_summary(date_from=df, date_to=dt, users_filter=filt)
        if raw:
            return _dumps(
                {
                    "productivity_detail": detail,
                    "productivity_stats": stats,
                    "analytics_metrics": analytics.get("Metrics")
                    if isinstance(analytics, dict)
                    else None,
                    "top_risks": analytics.get("Risks") if isinstance(analytics, dict) else None,
                }
            )
        return _dumps(
            format_productivity_rollup(detail, stats, analytics, user_id=user_id)
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def list_reports() -> str:
    """List scheduled report mailing settings and background processing tasks.

    ReportTypes are labeled with public console names when known.
    """
    try:
        client = _get_client()
        scheduled = client.get_reports_settings() or []
        enriched = []
        for row in scheduled if isinstance(scheduled, list) else []:
            if not isinstance(row, dict):
                continue
            item = dict(row)
            item["ReportTypesLabeled"] = label_report_types(row.get("ReportTypes"))
            enriched.append(item)
        return _dumps(
            {
                "scheduled_reports": enriched,
                "processing_tasks": client.get_processing_tasks(),
            }
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


def main() -> None:
    get_settings()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
