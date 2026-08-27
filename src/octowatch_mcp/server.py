"""OctoWatch MCP server — read-only tools for Claude / Cursor / ChatGPT."""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Callable
from functools import wraps
from typing import Annotated, Any, Literal, TypeVar

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from octowatch_mcp import __version__
from octowatch_mcp.client import (
    ACCOUNT_READONLY_SOURCES,
    ANALYTICS_VIEWS,
    DASHBOARD_WIDGETS,
    DIRECTORY_SOURCES,
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
from octowatch_mcp.toolsets import apply_toolsets

logger = logging.getLogger("octowatch_mcp")

_RO = ToolAnnotations(read_only_hint=True, open_world_hint=True)

_TOOL_ROUTING = (
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
)

mcp = MCPServer(
    "octowatch",
    version=__version__,
    website_url="https://octowatchdlp.com",
    instructions=(
        "Read-only OctoWatch DLP Cloud. Prefer period=today|yesterday|last_7_days|last_30_days "
        "or date_from/date_to (date-only = full day, date_to ends 23:59:59). "
        "Filters: group_id = TreeviewUsers NodeType=14; user_id = NodeType=1 (AliasID). "
        "GetUsersGroups2 Type 1=group/2=user is NOT POST NodeType.\n" + _TOOL_ROUTING
    ),
)

_client: OctoWatchClient | None = None
RISKS_FETCH_ALL_CAP = 2000
DEFAULT_LIMIT = 100
MAX_LIMIT = 500

F = TypeVar("F", bound=Callable[..., Any])

PeriodArg = Annotated[
    str | None,
    Field(
        description="Relative period: today|yesterday|last_7_days|last_30_days "
        "(wins over date_from/date_to when set)."
    ),
]
DateFromArg = Annotated[
    str | None,
    Field(description="Start datetime YYYY-MM-DD or YYYY-MM-DD HH:MM:SS (full day if date-only)."),
]
DateToArg = Annotated[
    str | None,
    Field(description="End datetime; date-only covers until 23:59:59 that day."),
]
GroupIdArg = Annotated[
    int | None,
    Field(description="Group filter: TreeviewUsers NodeType=14 (console group id)."),
]
UserIdArg = Annotated[
    int | None,
    Field(description="User filter: AliasID as TreeviewUsers NodeType=1."),
]
LimitArg = Annotated[
    int,
    Field(ge=1, le=MAX_LIMIT, description=f"Max rows to return (1–{MAX_LIMIT})."),
]
OffsetArg = Annotated[int, Field(ge=0, description="Pagination offset (0-based).")]
FilterKeyArg = Annotated[
    str | None,
    Field(description="Optional text filter passed to the Cloud API FilterKey."),
]


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


def _map_tool_errors(fn: F) -> F:
    """Convert known failures to ToolError so hosts get is_error=True."""

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except ToolError:
            raise
        except OctoWatchAPIError as exc:
            # client messages already include "→ HTTP N:"; don't double-prefix
            detail = str(exc)
            logger.info("Tool %s API error: %s", fn.__name__, detail)
            raise ToolError(detail) from exc
        except (ValueError, TypeError, httpx.HTTPError) as exc:
            logger.info("Tool %s error: %s", fn.__name__, exc)
            raise ToolError(str(exc)) from exc

    return wrapper  # type: ignore[return-value]


def _get_client() -> OctoWatchClient:
    global _client
    if _client is None:
        _client = OctoWatchClient(get_settings())
    return _client


def _tool_payload(data: Any) -> dict[str, Any]:
    """MCP structured output requires a JSON object; wrap lists/scalars."""
    if isinstance(data, dict):
        return data
    return {"data": data}


def _session_identity() -> dict[str, Any]:
    """Host/account payload for whoami tool and resource (no password)."""
    s = get_settings()
    client = _get_client()
    client.ensure_auth()
    return {
        "version": __version__,
        "api_base": s.api_base,
        "email": s.email,
        "is_demo": s.is_demo,
        "public_id": client._public_id,
        "token_expires_in": max(0, int(client._expires_at - time.time())),
        "warning": (
            "DEMO account — do not put production passwords in MCP config." if s.is_demo else None
        ),
    }


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


def _configure_logging() -> None:
    root = logging.getLogger("octowatch_mcp")
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    root.propagate = False


# --- tools --------------------------------------------------------------------


@mcp.tool(title="Who am I", annotations=_RO)
@_map_tool_errors
def octowatch_whoami() -> dict[str, Any]:
    """Show which OctoWatch API host and account the MCP server is using (password never returned)."""
    return _session_identity()


@mcp.tool(title="List users and groups", annotations=_RO)
@_map_tool_errors
def list_users_groups(refresh: bool = False) -> dict[str, Any]:
    """List users and groups tree (GetUsersGroups2). Type 0=root, 1=group, 2=user.

    These Type values are for the UI tree only. For report POST filters use
    NodeType 14=group and NodeType 1=user (AliasID).
    Cached ~5 min per MCP session; pass refresh=true to force reload.
    """
    return _tool_payload(_get_client().get_users_groups(force_refresh=refresh))


@mcp.tool(title="List DLP risks", annotations=_RO)
@_map_tool_errors
def list_risks(
    period: PeriodArg = None,
    date_from: DateFromArg = None,
    date_to: DateToArg = None,
    group_id: GroupIdArg = None,
    user_id: UserIdArg = None,
    mode: Annotated[
        Literal["summary", "raw"],
        Field(description="summary = by_user/by_rule rollup; raw = Risks/Overall2 page."),
    ] = "summary",
    offset: OffsetArg = 0,
    limit: LimitArg = 100,
    fetch_all: bool = False,
    compact: bool = True,
) -> dict[str, Any]:
    """List or summarize DLP/rule Risks for a period.

    Use for: policy/keyword/USB/AI rule hits. Default mode=summary
    (by_user from Analytics/Overall; by_rule/by_day/sample from Risks/Overall2).
    Not for idle time (get_idle_summary) or timetable deviations (list_anomalies).
    """
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
        return {
            "TotalRecords": data.get("TotalRecords"),
            "StartFrom": data.get("StartFrom"),
            "NumRecords": len(items),
            "List": items,
        }

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

    return {
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
                None if fetch_all else "by_rule/by_day/sample are from the fetched page only"
            ),
        },
    }


@mcp.tool(title="List formal alerts", annotations=_RO)
@_map_tool_errors
def list_anomalies(
    period: PeriodArg = None,
    date_from: DateFromArg = None,
    date_to: DateToArg = None,
    group_id: GroupIdArg = None,
    user_id: UserIdArg = None,
    offset: OffsetArg = 0,
    limit: LimitArg = 100,
    filter_key: FilterKeyArg = None,
    compact: bool = True,
) -> dict[str, Any]:
    """List formal Alerts / deviations (POST /api/Alerts/Overall2).

    Use for: lateness, overtime, unusual app-share, timetable-fired alerts.
    Do NOT use for idle/inactive duration — that is get_idle_summary (InactiveTime).
    Do NOT use for DLP keyword/USB policy hits — that is list_risks.
    """
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
    return {
        "TotalRecords": data.get("TotalRecords"),
        "NumRecords": len(items),
        "List": items,
        "note": "Formal Alerts only. For idle duration use get_idle_summary.",
    }


@mcp.tool(title="Idle time summary", annotations=_RO)
@_map_tool_errors
def get_idle_summary(
    period: PeriodArg = None,
    date_from: DateFromArg = None,
    date_to: DateToArg = None,
    group_id: GroupIdArg = None,
    user_id: UserIdArg = None,
    min_idle_hours: Annotated[
        float | None,
        Field(ge=0, description="Only include users with InactiveTime >= this many hours."),
    ] = None,
) -> dict[str, Any]:
    """Rank users by inactive (idle) time from Productivity/Overall3.

    Use for: 'who was idle longest?', 'idle > N hours', InactiveTime totals.
    Do NOT use list_anomalies for idle — Alerts are formal deviations only.
    """
    df, dt = _period(period, date_from, date_to)
    detail = _get_client().productivity(
        date_from=df,
        date_to=dt,
        users_filter=_filter(group_id, user_id),
    )
    return format_idle_summary(
        detail,
        user_id=user_id,
        min_idle_hours=min_idle_hours,
    )


@mcp.tool(title="Activity summary", annotations=_RO)
@_map_tool_errors
def get_activity_summary(
    period: PeriodArg = None,
    date_from: DateFromArg = None,
    date_to: DateToArg = None,
    group_id: GroupIdArg = None,
    user_id: UserIdArg = None,
    top_n: Annotated[int, Field(ge=1, le=100, description="How many top apps/sites to keep.")] = 15,
    raw: bool = False,
) -> dict[str, Any]:
    """Top apps and sites by ActiveTime (POST /api/Activity/Overall2)."""
    df, dt = _period(period, date_from, date_to)
    data = _get_client().activity(
        date_from=df,
        date_to=dt,
        users_filter=_filter(group_id, user_id),
    )
    if raw:
        return _tool_payload(data)
    return format_activity_top(data, top_n=max(1, min(top_n, 100)), user_id=user_id)


@mcp.tool(title="Timesheet", annotations=_RO)
@_map_tool_errors
def get_timesheet(
    period: PeriodArg = None,
    date_from: DateFromArg = None,
    date_to: DateToArg = None,
    group_id: GroupIdArg = None,
    user_id: UserIdArg = None,
    raw: bool = False,
) -> dict[str, Any]:
    """Timesheet / attendance summary (POST /api/TimeSheet/Overall2)."""
    df, dt = _period(period, date_from, date_to)
    data = _get_client().timesheet(
        date_from=df,
        date_to=dt,
        users_filter=_filter(group_id, user_id),
    )
    if raw:
        return _tool_payload(data)
    return format_timesheet(data, user_id=user_id)


@mcp.tool(title="Productivity summary", annotations=_RO)
@_map_tool_errors
def get_productivity_summary(
    period: PeriodArg = None,
    date_from: DateFromArg = None,
    date_to: DateToArg = None,
    group_id: GroupIdArg = None,
    user_id: UserIdArg = None,
    raw: bool = False,
) -> dict[str, Any]:
    """Per-user productivity rollup (Overall3 + stats + Analytics metrics)."""
    df, dt = _period(period, date_from, date_to)
    client = _get_client()
    filt = _filter(group_id, user_id)
    detail = client.productivity(date_from=df, date_to=dt, users_filter=filt)
    stats = client.productivity_stats(date_from=df, date_to=dt, users_filter=filt)
    analytics = client.analytics_summary(date_from=df, date_to=dt, users_filter=filt)
    if raw:
        return {
            "productivity_detail": detail,
            "productivity_stats": stats,
            "analytics_metrics": analytics.get("Metrics") if isinstance(analytics, dict) else None,
            "top_risks": analytics.get("Risks") if isinstance(analytics, dict) else None,
        }
    return format_productivity_rollup(detail, stats, analytics, user_id=user_id)


@mcp.tool(title="List reports", annotations=_RO)
@_map_tool_errors
def list_reports() -> dict[str, Any]:
    """List scheduled report mailing settings and background processing tasks."""
    client = _get_client()
    scheduled = client.get_reports_settings() or []
    enriched = []
    for row in scheduled if isinstance(scheduled, list) else []:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        item["ReportTypesLabeled"] = label_report_types(row.get("ReportTypes"))
        enriched.append(item)
    return {
        "scheduled_reports": enriched,
        "processing_tasks": client.get_processing_tasks(),
    }


@mcp.tool(title="Get analytics", annotations=_RO)
@_map_tool_errors
def get_analytics(
    view: Annotated[
        AnalyticsView,
        Field(description="Analytics view: overall|disciplina|activity|productivity."),
    ] = "overall",
    period: PeriodArg = None,
    date_from: DateFromArg = None,
    date_to: DateToArg = None,
    group_id: GroupIdArg = None,
    user_id: UserIdArg = None,
    compact: bool = True,
) -> dict[str, Any]:
    """Analytics rollups: view=overall|disciplina|activity|productivity."""
    df, dt = _period(period, date_from, date_to)
    data = _get_client().analytics_view(
        view,
        date_from=df,
        date_to=dt,
        users_filter=_filter(group_id, user_id),
    )
    return {
        "view": view,
        "endpoint": ANALYTICS_VIEWS[view],
        "data": _maybe_compact(data, compact),
    }


@mcp.tool(title="Get dashboard widget", annotations=_RO)
@_map_tool_errors
def get_dashboard(
    widget: Annotated[
        DashboardWidget,
        Field(description="Dashboard widget id (users, risks, applications, …)."),
    ] = "users",
    period: PeriodArg = None,
    date_from: DateFromArg = None,
    date_to: DateToArg = None,
    group_id: GroupIdArg = None,
    user_id: UserIdArg = None,
    num_screens: Annotated[int, Field(ge=1, le=50, description="Screens tile count.")] = 6,
    compact: bool = True,
) -> dict[str, Any]:
    """Dashboard widgets (metadata only; screenshot blobs stripped when compact)."""
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
    return {
        "widget": widget,
        "endpoint": DASHBOARD_WIDGETS[widget],
        "data": _maybe_compact(data, compact),
    }


@mcp.tool(title="Chronometry", annotations=_RO)
@_map_tool_errors
def get_chrono(
    period: PeriodArg = None,
    date_from: DateFromArg = None,
    date_to: DateToArg = None,
    group_id: GroupIdArg = None,
    user_id: UserIdArg = None,
    offset: OffsetArg = 0,
    limit: LimitArg = 100,
    filter_key: FilterKeyArg = None,
    compact: bool = True,
) -> dict[str, Any]:
    """Chronometry timeline (POST /api/Chrono/Overall2)."""
    df, dt = _period(period, date_from, date_to)
    data = _get_client().chrono(
        date_from=df,
        date_to=dt,
        users_filter=_filter(group_id, user_id),
        offset=max(0, offset),
        num_rows=_cap(limit),
        filter_key=filter_key,
    )
    return _tool_payload(_maybe_compact(data, compact, limit))


@mcp.tool(title="Day structure", annotations=_RO)
@_map_tool_errors
def get_day_structure(
    mode: Annotated[
        Literal["list", "detail"],
        Field(description="list = DayStructureList; detail = GetDayStructure (needs user_id)."),
    ] = "list",
    period: PeriodArg = None,
    date_from: DateFromArg = None,
    date_to: DateToArg = None,
    group_id: GroupIdArg = None,
    user_id: UserIdArg = None,
    productivity_filter: Annotated[int, Field(ge=0, le=4)] = 0,
    activity_type_filter: Annotated[int, Field(ge=0, le=2)] = 0,
    compact: bool = True,
) -> dict[str, Any]:
    """Day structure: mode=list (DayStructureList) or detail (GetDayStructure).

    detail requires user_id. Filters match console: ProductivityFilter 0–4,
    ActivityTypeFilter 0–2 (defaults 0).
    """
    df, dt = _period(period, date_from, date_to)
    client = _get_client()
    if mode == "detail":
        if user_id is None:
            raise ToolError("user_id (AliasID) is required for mode=detail")
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
    return {"mode": mode, "data": _maybe_compact(data, compact)}


@mcp.tool(title="List monitoring", annotations=_RO)
@_map_tool_errors
def list_monitoring(
    kind: Annotated[
        MonitoringKind,
        Field(description="Monitoring table: Sites|Apps|Keystrokes|Mail|…"),
    ],
    period: PeriodArg = None,
    date_from: DateFromArg = None,
    date_to: DateToArg = None,
    group_id: GroupIdArg = None,
    user_id: UserIdArg = None,
    offset: OffsetArg = 0,
    limit: LimitArg = 100,
    filter_key: FilterKeyArg = None,
    filter_objects: Annotated[
        str | None,
        Field(description="Optional FilterObjects JSON/string for Monitoring POST."),
    ] = None,
    compact: bool = True,
) -> dict[str, Any]:
    """Single Monitoring list (Sites, Apps, Screens, Keystrokes, Mail, …).

    For keyword search across many Monitoring kinds (console Tools → Search),
    use search_monitoring(filter_key=…) instead of calling this 13–19 times.

    Sensitive kinds return text truncated when compact=true. No binary media.
    """
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
    return {
        "kind": kind,
        "endpoint": f"/api/Monitoring/{kind}",
        "data": _maybe_compact(data, compact, limit),
        "sensitive": kind
        in ("Keystrokes", "Clipboard1", "Mail", "Messengers", "WebForms", "Screens"),
    }


@mcp.tool(title="Search monitoring", annotations=_RO)
@_map_tool_errors
def search_monitoring(
    filter_key: Annotated[
        str,
        Field(min_length=1, description="Keyword for Tools → Search fan-out across Monitoring."),
    ],
    period: PeriodArg = None,
    date_from: DateFromArg = None,
    date_to: DateToArg = None,
    group_id: GroupIdArg = None,
    user_id: UserIdArg = None,
    offset: OffsetArg = 0,
    per_source_limit: Annotated[int, Field(ge=1, le=100)] = 20,
    max_rows: Annotated[int, Field(ge=1, le=200)] = 50,
    kinds: Annotated[
        str | None,
        Field(description="Optional comma-separated kinds, e.g. Sites,Apps,Mail."),
    ] = None,
) -> dict[str, Any]:
    """Console Tools → Search: parallel Monitoring fan-out with FilterKey.

    Use for: 'find keyword X across activity' (sites/apps/keys/mail/files/…).
    Prefer this over calling list_monitoring many times.
    Not for Risks (list_risks), idle (get_idle_summary), or formal Alerts
    (list_anomalies). Does not search SearchQueries.

    kinds: optional comma-separated subset (e.g. "Sites,Apps,Mail" or
    "sites,mail"). Default = all Tools Search sources.
    """
    fk = (filter_key or "").strip()
    if not fk:
        raise ToolError("filter_key is required")
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
    return _tool_payload(data)


@mcp.tool(title="Activity detail", annotations=_RO)
@_map_tool_errors
def get_activity_detail(
    mode: Annotated[
        Literal["activity_window", "category_window"],
        Field(
            description="activity_window needs activity_name; category_window needs category_guid."
        ),
    ] = "activity_window",
    period: PeriodArg = None,
    date_from: DateFromArg = None,
    date_to: DateToArg = None,
    group_id: GroupIdArg = None,
    user_id: UserIdArg = None,
    activity_name: str | None = None,
    is_website: bool = False,
    category_guid: str | None = None,
    compact: bool = True,
) -> dict[str, Any]:
    """Activity drill-down: ActivityWindow (needs activity_name) or CategoryWindow (needs category_guid)."""
    df, dt = _period(period, date_from, date_to)
    client = _get_client()
    filt = _filter(group_id, user_id)
    if mode == "category_window":
        if not category_guid:
            raise ToolError("category_guid is required for category_window")
        data = client.category_window(
            guid=category_guid,
            date_from=df,
            date_to=dt,
            users_filter=filt,
        )
    else:
        if not activity_name:
            raise ToolError("activity_name is required for activity_window")
        data = client.activity_window(
            activity_name=activity_name,
            is_website=is_website,
            date_from=df,
            date_to=dt,
            users_filter=filt,
        )
    return {"mode": mode, "data": _maybe_compact(data, compact)}


@mcp.tool(title="List online presence", annotations=_RO)
@_map_tool_errors
def list_online(
    period: PeriodArg = None,
    date_from: DateFromArg = None,
    date_to: DateToArg = None,
    group_id: GroupIdArg = None,
    user_id: UserIdArg = None,
    compact: bool = True,
) -> dict[str, Any]:
    """Online presence (POST /api/Live/Overall2). No webcam or live stream frames."""
    df, dt = _period(period, date_from, date_to)
    data = _get_client().live_overall(
        date_from=df,
        date_to=dt,
        users_filter=_filter(group_id, user_id),
    )
    return _tool_payload(_maybe_compact(data, compact))


@mcp.tool(title="Stream metadata", annotations=_RO)
@_map_tool_errors
def list_stream_meta(
    source: Annotated[
        Literal["which_content", "videos", "downloads"],
        Field(description="which_content/videos need user_id; downloads is export list."),
    ] = "which_content",
    period: PeriodArg = None,
    date_from: DateFromArg = None,
    date_to: DateToArg = None,
    user_id: UserIdArg = None,
    compact: bool = True,
) -> dict[str, Any]:
    """Desktop video metadata (SPA GET contracts; no DownloadVideo).

    which_content: needs user_id; uses DateTo (or period end) as DateTime.
    videos: needs user_id + DateFrom/DateTo (UserID header).
    downloads: Bearer only (exported file list).
    """
    df, dt = _period(period, date_from, date_to)
    if source in ("which_content", "videos") and user_id is None:
        raise ToolError(f"{source} requires user_id (AliasID / UserID)")
    data = _get_client().stream_meta(
        source,
        date_from=df,
        date_to=dt,
        alias_id=user_id,
        at=dt,
    )
    return {
        "source": source,
        "endpoint": STREAM_META_SOURCES[source],
        "data": _maybe_compact(data, compact),
    }


@mcp.tool(title="List directory", annotations=_RO)
@_map_tool_errors
def list_directory(
    source: Annotated[
        Literal[
            "users_groups",
            "users",
            "groups",
            "list_groups",
            "computers",
            "additional_users",
            "additional_rights",
        ],
        Field(description="Directory Get source."),
    ] = "users_groups",
    refresh: bool = False,
) -> dict[str, Any]:
    """Directory reads: users/groups tree, users, groups, computers, additional operators.

    users_groups is session-cached (~5 min); pass refresh=true to force reload.
    """
    data = _get_client().get_directory(source, force_refresh=refresh)
    return {
        "source": source,
        "endpoint": DIRECTORY_SOURCES[source],
        "data": data,
    }


@mcp.tool(title="Get user info", annotations=_RO)
@_map_tool_errors
def get_user_info(
    source: Annotated[
        Literal[
            "user_data",
            "tooltip",
            "group",
            "computer",
            "users_from_computer",
        ],
        Field(description="User/computer detail source."),
    ] = "user_data",
    period: PeriodArg = None,
    date_from: DateFromArg = None,
    date_to: DateToArg = None,
    user_id: UserIdArg = None,
    computer_guid: str | None = None,
    compact: bool = True,
) -> dict[str, Any]:
    """User/computer detail reads (SPA GET headers).

    user_data / tooltip / group: need user_id (AliasID).
    group = group *path* for that user (not load-by-GroupID).
    computer / users_from_computer: need computer_guid (ComputerGuid).
    """
    df, dt = _period(period, date_from, date_to)
    data = _get_client().get_user_info(
        source,
        alias_id=user_id,
        computer_guid=computer_guid,
        date_from=df,
        date_to=dt,
    )
    return {
        "source": source,
        "endpoint": USER_INFO_SOURCES[source][1],
        "data": _maybe_compact(data, compact),
    }


@mcp.tool(title="Account read-only", annotations=_RO)
@_map_tool_errors
def get_account_readonly(
    source: Annotated[
        Literal[
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
        ],
        Field(description="Account/profile/license Get source (no Set*/PIN)."),
    ] = "account_settings",
    profiles_type: int | None = None,
    user_id: UserIdArg = None,
    alias_type: int | None = None,
    profile_id: int | None = None,
    computer_guid: str | None = None,
    compact: bool = True,
) -> dict[str, Any]:
    """Read-only account/profile/license Gets (SPA header contracts).

    profiles: GetProfiles2 — ProfilesType 0|1|2; optional user_id + alias_type
    (1=user, 14=group); defaults AliasID/AliasType=-1.
    timetable/rules/profile_settings/computer_settings: require profile_id.
    computer_profiles: optional computer_guid (Guid header).
    """
    data = _get_client().get_account_readonly(
        source,
        profiles_type=profiles_type,
        alias_id=user_id,
        alias_type=alias_type,
        profile_id=profile_id,
        computer_guid=computer_guid,
    )
    return {
        "source": source,
        "endpoint": ACCOUNT_READONLY_SOURCES[source],
        "data": _maybe_compact(data, compact),
    }


@mcp.tool(title="API coverage matrix", annotations=_RO)
@_map_tool_errors
def list_api_coverage() -> dict[str, Any]:
    """Static gap matrix: which console APIs are covered vs intentional out-of-scope."""
    return coverage_summary()


# --- resources ----------------------------------------------------------------


@mcp.resource("octowatch://coverage", mime_type="application/json", title="API coverage")
def resource_coverage() -> dict[str, Any]:
    """Static gap matrix of console API coverage (same data as list_api_coverage)."""
    return coverage_summary()


@mcp.resource(
    "octowatch://tool-routing",
    mime_type="text/plain",
    title="Tool routing guide",
)
def resource_tool_routing() -> str:
    """When-which-tool routing text for SecOps queries."""
    return _TOOL_ROUTING


@mcp.resource("octowatch://whoami", mime_type="application/json", title="Session identity")
def resource_whoami() -> dict[str, Any]:
    """Current API host and account (password never included). Live call."""
    try:
        return _session_identity()
    except OctoWatchAPIError as exc:
        raise ResourceError(str(exc)) from exc
    except (ValueError, TypeError, httpx.HTTPError, OSError) as exc:
        raise ResourceError(str(exc)) from exc


# --- prompts ------------------------------------------------------------------


@mcp.prompt(title="Daily risks brief")
def daily_risks_brief(
    period: Annotated[
        str,
        Field(description="Period: today|yesterday|last_7_days|last_30_days"),
    ] = "today",
) -> str:
    """Summarize DLP risks for a period using the recommended tool sequence."""
    return (
        f"Produce a short SecOps risks brief for OctoWatch period={period}.\n"
        "1) Call list_risks(period=..., mode=summary).\n"
        "2) Highlight top users (by_user) and top rules (by_rule).\n"
        "3) If needed, call list_users_groups to map AliasIDs to names.\n"
        "4) Do not use list_anomalies for DLP hits or get_idle_summary for policy hits.\n"
        "Keep the answer concise with bullet points."
    )


@mcp.prompt(title="Idle review")
def idle_review(
    period: Annotated[
        str,
        Field(description="Period: today|yesterday|last_7_days|last_30_days"),
    ] = "yesterday",
    group_id: Annotated[
        str,
        Field(description="Optional group id (NodeType=14). Empty = all users."),
    ] = "",
) -> str:
    """Find who was idle longest using get_idle_summary (not list_anomalies)."""
    group_line = (
        f"Filter to group_id={group_id.strip()} (TreeviewUsers NodeType=14).\n"
        if group_id.strip()
        else "Include all users/groups.\n"
    )
    return (
        f"Review idle/inactive time for period={period}.\n"
        f"{group_line}"
        "1) Call get_idle_summary(period=..., group_id=... if set).\n"
        "2) Rank by InactiveTime; call out anyone with unusually high idle.\n"
        "3) Do NOT use list_anomalies for idle duration — that tool is formal Alerts only.\n"
        "Return a short ranked list."
    )


@mcp.prompt(title="User activity drill-down")
def user_activity_drilldown(
    user_id: Annotated[str, Field(description="User AliasID (NodeType=1).")],
    period: Annotated[
        str,
        Field(description="Period: today|yesterday|last_7_days|last_30_days"),
    ] = "today",
) -> str:
    """Drill into one user's apps/sites and optional activity window."""
    return (
        f"Investigate activity for user_id={user_id} period={period}.\n"
        "1) get_user_info(source=user_data, user_id=...).\n"
        "2) get_activity_summary(period=..., user_id=...).\n"
        "3) Optionally get_productivity_summary and get_timesheet for the same user/period.\n"
        "4) If a specific app/site stands out, get_activity_detail(activity_name=..., user_id=...).\n"
        "Summarize top apps/sites and any anomalies in plain language."
    )


@mcp.prompt(title="Monitoring keyword hunt")
def monitoring_keyword_hunt(
    filter_key: Annotated[str, Field(description="Keyword to search across Monitoring.")],
    period: Annotated[
        str,
        Field(description="Period: today|yesterday|last_7_days|last_30_days"),
    ] = "last_7_days",
) -> str:
    """Search Monitoring via Tools Search (search_monitoring), not repeated list_monitoring."""
    return (
        f"Hunt for keyword {filter_key!r} across Monitoring for period={period}.\n"
        "1) Call search_monitoring(filter_key=..., period=...) once "
        "(Tools Search fan-out). Do NOT loop list_monitoring for each kind.\n"
        "2) Summarize hits by kind (Sites/Apps/Keystrokes/Mail/Files/…).\n"
        "3) If DLP policy hits are needed separately, use list_risks — not this search.\n"
        "Return compact findings with user names/ids when present."
    )


def main(argv: list[str] | None = None) -> None:
    import argparse

    _configure_logging()
    parser = argparse.ArgumentParser(prog="octowatch-mcp")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport (default: stdio).",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host for streamable-http (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port for streamable-http (default: 8000).",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    try:
        apply_toolsets(mcp)
    except ValueError as exc:
        logger.error("%s", exc)
        raise SystemExit(2) from exc
    logger.info(
        "Starting octowatch-mcp %s (api_base=%s, demo=%s, transport=%s)",
        __version__,
        settings.api_base,
        settings.is_demo,
        args.transport,
    )
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        if args.host not in ("127.0.0.1", "localhost", "::1"):
            logger.warning(
                "Binding streamable-http to %s exposes demo/prod credentials on the network",
                args.host,
            )
        mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
