"""OctoWatch MCP server — read-only tools for Claude / Cursor / ChatGPT."""

from __future__ import annotations

import json
import time
from typing import Any, Literal

import httpx
from mcp.server.mcpserver import MCPServer

from octowatch_mcp import __version__
from octowatch_mcp.client import (
    ACCOUNT_READONLY_SOURCES,
    ANALYTICS_VIEWS,
    DASHBOARD_WIDGETS,
    DIRECTORY_SOURCES,
    MONITORING_KINDS,
    STREAM_META_SOURCES,
    USER_INFO_SOURCES,
    OctoWatchAPIError,
    OctoWatchClient,
)
from octowatch_mcp.compact import compact_api_payload
from octowatch_mcp.config import get_settings
from octowatch_mcp.coverage import coverage_summary
from octowatch_mcp.filters import build_users_filter
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
        "Read-only OctoWatch DLP Cloud. Prefer period=today|yesterday|last_7_days|last_30_days "
        "or date_from/date_to (date-only = full day, date_to ends 23:59:59). "
        "Filters: group_id = TreeviewUsers NodeType=14; user_id = NodeType=1 (AliasID). "
        "GetUsersGroups2 Type 1=group/2=user is NOT POST NodeType.\n"
        "WHEN WHICH TOOL (do not confuse):\n"
        "- Idle / inactive time / 'who was idle' -> get_idle_summary (InactiveTime). "
        "NOT list_anomalies.\n"
        "- Formal deviations (lateness, overtime, timetable alerts) -> list_anomalies "
        "(Alerts/Overall2). Empty is normal on 24h schedules.\n"
        "- DLP/rule hits (keywords, USB, policy) -> list_risks mode=summary "
        "(by_user from Analytics; details from Risks/Overall2).\n"
        "- Top apps/sites by time -> get_activity_summary; drill-down -> get_activity_detail.\n"
        "- Productivity % / productive vs unproductive -> get_productivity_summary.\n"
        "- Attendance / worked hours vs timetable -> get_timesheet.\n"
        "- Chronometry timeline -> get_chrono.\n"
        "- Day segments structure -> get_day_structure.\n"
        "- Keyword find across sites/apps/keys/mail/files (Tools Search) -> "
        "search_monitoring(filter_key=...). Do NOT loop list_monitoring for search.\n"
        "- One Monitoring table only -> list_monitoring(kind=Sites|Apps|Keystrokes|...).\n"
        "- Dashboard tiles -> get_dashboard(widget=...). Analytics charts -> get_analytics(view=...).\n"
        "- Online presence -> list_online. Video metadata -> list_stream_meta "
        "(no screenshot/video binary downloads).\n"
        "- Users/groups tree -> list_users_groups or list_directory; person card -> get_user_info.\n"
        "- Profiles/license/settings (Get*) -> get_account_readonly. Reports queue -> list_reports.\n"
        "- Coverage gaps -> list_api_coverage. Account/host -> octowatch_whoami.\n"
        "No writes. Demo credentials may be active - never assume production data."
    ),
)

_client: OctoWatchClient | None = None
RISKS_FETCH_ALL_CAP = 2000
DEFAULT_LIMIT = 100
MAX_LIMIT = 500

_TOOL_ERRORS = (
    OctoWatchAPIError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    OSError,
    RuntimeError,
    httpx.HTTPError,
)

MonitoringKind = Literal[
    "Sites",
    "Apps",
    "Installs",
    "Screens",
    "Keystrokes",
    "Clipboard1",
    "SearchQueries",
    "WebForms",
    "Messengers",
    "Mail",
    "WebcamAudio",
    "Files",
    "Crawler",
    "USBExplorer",
    "Prints",
    "NetworkInterfaces",
    "WiFis",
    "Traffic",
    "TrafficSum",
]

DashboardWidget = Literal[
    "users",
    "screens",
    "risks",
    "alerts",
    "top10_risks_alerts",
    "productivity_by_day",
    "applications",
    "websites",
    "top10_users",
    "top10_groups",
    "metric1",
]

AnalyticsView = Literal["overall", "disciplina", "activity", "productivity"]


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


def _filter(group_id: int | None, user_id: int | None = None):
    return build_users_filter(group_id=group_id, user_id=user_id)


def _cap(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))


def _maybe_compact(data: Any, compact: bool, limit: int = DEFAULT_LIMIT) -> Any:
    if not compact:
        return data
    return compact_api_payload(data, list_cap=_cap(limit))


# --- existing tools -----------------------------------------------------------


@mcp.tool()
def octowatch_whoami() -> str:
    """Show which OctoWatch API host and account the MCP server is using (password never returned)."""
    try:
        s = get_settings()
        client = _get_client()
        client.ensure_auth()
        # Prefer cached session; only hit login-jwt when unauthenticated.
        login = {
            "PublicID": client._public_id,
            "ExpiresIn": max(0, int(client._expires_at - time.time())),
        }
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
def list_users_groups(refresh: bool = False) -> str:
    """List users and groups tree (GetUsersGroups2). Type 0=root, 1=group, 2=user.

    These Type values are for the UI tree only. For report POST filters use
    NodeType 14=group and NodeType 1=user (AliasID).
    Cached ~5 min per MCP session; pass refresh=true to force reload.
    """
    try:
        data = _get_client().get_users_groups(force_refresh=refresh)
        return _dumps(data)
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

    Use for: policy/keyword/USB/AI rule hits. Default mode=summary
    (by_user from Analytics/Overall; by_rule/by_day/sample from Risks/Overall2).
    Not for idle time (get_idle_summary) or timetable deviations (list_anomalies).
    """
    try:
        df, dt = _period(period, date_from, date_to)
        client = _get_client()
        filt = _filter(group_id, user_id)
        page_size = _cap(limit)

        if mode == "raw":
            data = client.risks(
                date_from=df,
                date_to=dt,
                users_filter=filt,
                offset=max(0, offset),
                num_rows=page_size,
            )
            items = list(data.get("List") or [])
            if user_id is not None:
                items = filter_by_alias_id(items, user_id)
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
            items = list(page.get("List") or [])
            if user_id is not None:
                items = filter_by_alias_id(items, user_id)
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
            items = list(page.get("List") or [])
            if user_id is not None:
                items = filter_by_alias_id(items, user_id)
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

    Use for: lateness, overtime, unusual app-share, timetable-fired alerts.
    Do NOT use for idle/inactive duration — that is get_idle_summary (InactiveTime).
    Do NOT use for DLP keyword/USB policy hits — that is list_risks.
    """
    try:
        df, dt = _period(period, date_from, date_to)
        data = _get_client().anomalies(
            date_from=df,
            date_to=dt,
            users_filter=_filter(group_id, user_id),
            offset=max(0, offset),
            num_rows=_cap(limit),
            filter_key=filter_key,
        )
        items = list(data.get("List") or [])
        if user_id is not None:
            items = filter_by_alias_id(items, user_id)
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

    Use for: 'who was idle longest?', 'idle > N hours', InactiveTime totals.
    Do NOT use list_anomalies for idle — Alerts are formal deviations only.
    """
    try:
        df, dt = _period(period, date_from, date_to)
        detail = _get_client().productivity(
            date_from=df,
            date_to=dt,
            users_filter=_filter(group_id, user_id),
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
            users_filter=_filter(group_id, user_id),
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
    """Timesheet / attendance summary (POST /api/TimeSheet/Overall2)."""
    try:
        df, dt = _period(period, date_from, date_to)
        data = _get_client().timesheet(
            date_from=df,
            date_to=dt,
            users_filter=_filter(group_id, user_id),
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
        filt = _filter(group_id, user_id)
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
    """List scheduled report mailing settings and background processing tasks."""
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


# --- new grouped tools --------------------------------------------------------


@mcp.tool()
def get_analytics(
    view: AnalyticsView = "overall",
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
    user_id: int | None = None,
    compact: bool = True,
) -> str:
    """Analytics rollups: view=overall|disciplina|activity|productivity."""
    try:
        df, dt = _period(period, date_from, date_to)
        data = _get_client().analytics_view(
            view,
            date_from=df,
            date_to=dt,
            users_filter=_filter(group_id, user_id),
        )
        return _dumps(
            {
                "view": view,
                "endpoint": ANALYTICS_VIEWS[view],
                "data": _maybe_compact(data, compact),
            }
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def get_dashboard(
    widget: DashboardWidget = "users",
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
    user_id: int | None = None,
    num_screens: int = 6,
    compact: bool = True,
) -> str:
    """Dashboard widgets (metadata only; screenshot blobs stripped when compact)."""
    try:
        df, dt = _period(period, date_from, date_to)
        data = _get_client().dashboard_widget(
            widget,
            date_from=df,
            date_to=dt,
            users_filter=_filter(group_id, user_id),
            num_screens=num_screens,
            videos=False,
            screens=True,
        )
        return _dumps(
            {
                "widget": widget,
                "endpoint": DASHBOARD_WIDGETS[widget],
                "data": _maybe_compact(data, compact),
            }
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def get_chrono(
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
    """Chronometry timeline (POST /api/Chrono/Overall2)."""
    try:
        df, dt = _period(period, date_from, date_to)
        data = _get_client().chrono(
            date_from=df,
            date_to=dt,
            users_filter=_filter(group_id, user_id),
            offset=max(0, offset),
            num_rows=_cap(limit),
            filter_key=filter_key,
        )
        return _dumps(_maybe_compact(data, compact, limit))
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def get_day_structure(
    mode: Literal["list", "detail"] = "list",
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
    user_id: int | None = None,
    productivity_filter: int = 0,
    activity_type_filter: int = 0,
    compact: bool = True,
) -> str:
    """Day structure: mode=list (DayStructureList) or detail (GetDayStructure).

    detail requires user_id. Filters match console: ProductivityFilter 0–4,
    ActivityTypeFilter 0–2 (defaults 0).
    """
    try:
        df, dt = _period(period, date_from, date_to)
        client = _get_client()
        if mode == "detail":
            if user_id is None:
                return _dumps({"error": "user_id (AliasID) is required for mode=detail"})
            data = client.day_structure(
                user_id=user_id,
                date_from=df,
                date_to=dt,
                productivity_filter=productivity_filter,
                activity_type_filter=activity_type_filter,
            )
        else:
            data = client.day_structure_list(
                date_from=df,
                date_to=dt,
                users_filter=_filter(group_id, user_id),
            )
        return _dumps({"mode": mode, "data": _maybe_compact(data, compact)})
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def list_monitoring(
    kind: MonitoringKind,
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
    user_id: int | None = None,
    offset: int = 0,
    limit: int = 100,
    filter_key: str | None = None,
    filter_objects: str | None = None,
    compact: bool = True,
) -> str:
    """Single Monitoring list (Sites, Apps, Screens, Keystrokes, Mail, …).

    For keyword search across many Monitoring kinds (console Tools → Search),
    use search_monitoring(filter_key=…) instead of calling this 13–19 times.

    Sensitive kinds return text truncated when compact=true. No binary media.
    """
    try:
        if kind not in MONITORING_KINDS:
            return _dumps({"error": f"Unknown kind; choose from {sorted(MONITORING_KINDS)}"})
        df, dt = _period(period, date_from, date_to)
        data = _get_client().monitoring(
            kind,
            date_from=df,
            date_to=dt,
            users_filter=_filter(group_id, user_id),
            offset=max(0, offset),
            num_rows=_cap(limit),
            filter_key=filter_key,
            filter_objects=filter_objects,
            videos=False,
            screens=True,
        )
        return _dumps(
            {
                "kind": kind,
                "endpoint": f"/api/Monitoring/{kind}",
                "data": _maybe_compact(data, compact, limit),
                "sensitive": kind
                in ("Keystrokes", "Clipboard1", "Mail", "Messengers", "WebForms", "Screens"),
            }
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def search_monitoring(
    filter_key: str,
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
    user_id: int | None = None,
    offset: int = 0,
    per_source_limit: int = 20,
    max_rows: int = 50,
    kinds: str | None = None,
) -> str:
    """Console Tools → Search: parallel Monitoring fan-out with FilterKey.

    Use for: 'find keyword X across activity' (sites/apps/keys/mail/files/…).
    Prefer this over calling list_monitoring many times.
    Not for Risks (list_risks), idle (get_idle_summary), or formal Alerts
    (list_anomalies). Does not search SearchQueries.

    kinds: optional comma-separated subset (e.g. "Sites,Apps,Mail" or
    "sites,mail"). Default = all Tools Search sources.
    """
    try:
        fk = (filter_key or "").strip()
        if not fk:
            return _dumps({"error": "filter_key is required"})
        df, dt = _period(period, date_from, date_to)
        kind_list = [p.strip() for p in kinds.split(",")] if kinds else None
        data = _get_client().tools_search(
            filter_key=fk,
            date_from=df,
            date_to=dt,
            users_filter=_filter(group_id, user_id),
            offset=max(0, offset),
            per_source_limit=max(1, min(per_source_limit, 100)),
            max_rows=max(1, min(max_rows, 200)),
            kinds=kind_list,
        )
        return _dumps(data)
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def get_activity_detail(
    mode: Literal["activity_window", "category_window"] = "activity_window",
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
    user_id: int | None = None,
    activity_name: str | None = None,
    is_website: bool = False,
    category_guid: str | None = None,
    compact: bool = True,
) -> str:
    """Activity drill-down: ActivityWindow (needs activity_name) or CategoryWindow (needs category_guid)."""
    try:
        df, dt = _period(period, date_from, date_to)
        client = _get_client()
        filt = _filter(group_id, user_id)
        if mode == "category_window":
            if not category_guid:
                return _dumps({"error": "category_guid is required for category_window"})
            data = client.category_window(
                guid=category_guid,
                date_from=df,
                date_to=dt,
                users_filter=filt,
            )
        else:
            if not activity_name:
                return _dumps({"error": "activity_name is required for activity_window"})
            data = client.activity_window(
                activity_name=activity_name,
                is_website=is_website,
                date_from=df,
                date_to=dt,
                users_filter=filt,
            )
        return _dumps({"mode": mode, "data": _maybe_compact(data, compact)})
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def list_online(
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_id: int | None = None,
    user_id: int | None = None,
    compact: bool = True,
) -> str:
    """Online presence (POST /api/Live/Overall2). No webcam or live stream frames."""
    try:
        df, dt = _period(period, date_from, date_to)
        data = _get_client().live_overall(
            date_from=df,
            date_to=dt,
            users_filter=_filter(group_id, user_id),
        )
        return _dumps(_maybe_compact(data, compact))
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def list_stream_meta(
    source: Literal["which_content", "videos", "downloads"] = "which_content",
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    user_id: int | None = None,
    compact: bool = True,
) -> str:
    """Desktop video metadata (SPA GET contracts; no DownloadVideo).

    which_content: needs user_id; uses DateTo (or period end) as DateTime.
    videos: needs user_id + DateFrom/DateTo (UserID header).
    downloads: Bearer only (exported file list).
    """
    try:
        df, dt = _period(period, date_from, date_to)
        if source in ("which_content", "videos") and user_id is None:
            return _dumps({"error": f"{source} requires user_id (AliasID / UserID)"})
        data = _get_client().stream_meta(
            source,
            date_from=df,
            date_to=dt,
            alias_id=user_id,
            at=dt,
        )
        return _dumps(
            {
                "source": source,
                "endpoint": STREAM_META_SOURCES[source],
                "data": _maybe_compact(data, compact),
            }
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def list_directory(
    source: Literal[
        "users_groups",
        "users",
        "groups",
        "list_groups",
        "computers",
        "additional_users",
        "additional_rights",
    ] = "users_groups",
    refresh: bool = False,
) -> str:
    """Directory reads: users/groups tree, users, groups, computers, additional operators.

    users_groups is session-cached (~5 min); pass refresh=true to force reload.
    """
    try:
        data = _get_client().get_directory(source, force_refresh=refresh)
        return _dumps(
            {
                "source": source,
                "endpoint": DIRECTORY_SOURCES[source],
                "data": data,
            }
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def get_user_info(
    source: Literal[
        "user_data",
        "tooltip",
        "group",
        "computer",
        "users_from_computer",
    ] = "user_data",
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    user_id: int | None = None,
    computer_guid: str | None = None,
    compact: bool = True,
) -> str:
    """User/computer detail reads (SPA GET headers).

    user_data / tooltip / group: need user_id (AliasID).
    group = group *path* for that user (not load-by-GroupID).
    computer / users_from_computer: need computer_guid (ComputerGuid).
    """
    try:
        df, dt = _period(period, date_from, date_to)
        data = _get_client().get_user_info(
            source,
            alias_id=user_id,
            computer_guid=computer_guid,
            date_from=df,
            date_to=dt,
        )
        return _dumps(
            {
                "source": source,
                "endpoint": USER_INFO_SOURCES[source][1],
                "data": _maybe_compact(data, compact),
            }
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def get_account_readonly(
    source: Literal[
        "profiles",
        "computer_profiles",
        "timetable",
        "rules",
        "profile_settings",
        "computer_settings",
        "account_settings",
        "categories",
        "top_websites",
        "top_apps",
        "price_settings",
        "num_users",
        "license",
        "license_expired",
        "license_support",
        "reports",
        "processing_tasks",
    ] = "account_settings",
    profiles_type: int | None = None,
    user_id: int | None = None,
    alias_type: int | None = None,
    profile_id: int | None = None,
    computer_guid: str | None = None,
    compact: bool = True,
) -> str:
    """Read-only account/profile/license Gets (SPA header contracts).

    profiles: GetProfiles2 — ProfilesType 0|1|2; optional user_id + alias_type
    (1=user, 14=group); defaults AliasID/AliasType=-1.
    timetable/rules/profile_settings/computer_settings: require profile_id.
    computer_profiles: optional computer_guid (Guid header).
    """
    try:
        data = _get_client().get_account_readonly(
            source,
            profiles_type=profiles_type,
            alias_id=user_id,
            alias_type=alias_type,
            profile_id=profile_id,
            computer_guid=computer_guid,
        )
        return _dumps(
            {
                "source": source,
                "endpoint": ACCOUNT_READONLY_SOURCES[source],
                "data": _maybe_compact(data, compact),
            }
        )
    except _TOOL_ERRORS as exc:
        return _err(exc)


@mcp.tool()
def list_api_coverage() -> str:
    """Static gap matrix: which console APIs are covered vs intentional out-of-scope."""
    try:
        return _dumps(coverage_summary())
    except _TOOL_ERRORS as exc:
        return _err(exc)


def main() -> None:
    get_settings()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
