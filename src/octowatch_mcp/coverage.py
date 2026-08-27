"""Static API coverage matrix for list_api_coverage (mirrors docs/API.md)."""

from __future__ import annotations

from typing import Any

# status: covered | covered_compact | out_of_scope_write | out_of_scope_binary
#          | out_of_scope_not_in_console | intentional_skip

COVERAGE: list[dict[str, str]] = [
    # Auth
    {"area": "Auth", "endpoint": "GET /api/Access/login-jwt", "tool": "octowatch_whoami", "status": "covered"},
    {"area": "Auth", "endpoint": "GET /api/Access/refresh-token", "tool": "(client)", "status": "covered"},
    # Directory
    {
        "area": "Directory",
        "endpoint": "GET /api/Edit/GetUsersGroups2",
        "tool": "list_users_groups / list_directory",
        "status": "covered",
    },
    {
        "area": "Directory",
        "endpoint": "GET /api/Edit/GetUsers|GetGroups|GetListGroups|GetComputers2",
        "tool": "list_directory",
        "status": "covered",
    },
    {
        "area": "Directory",
        "endpoint": "GET /api/Edit/GetAdditionalUsers|GetAdditionalUsersRights",
        "tool": "list_directory",
        "status": "covered",
    },
    {
        "area": "Directory",
        "endpoint": "Edit user/group mutations (New/Rename/Move/Remove/…)",
        "tool": "—",
        "status": "out_of_scope_write",
    },
    # Risks / Alerts
    {
        "area": "Risks",
        "endpoint": "POST /api/Risks/Overall2",
        "tool": "list_risks",
        "status": "covered_compact",
    },
    {
        "area": "Alerts",
        "endpoint": "POST /api/Alerts/Overall2",
        "tool": "list_anomalies",
        "status": "covered_compact",
    },
    {
        "area": "Risks/Alerts",
        "endpoint": "ShowHide / SetMarker2 / RemoveRecord2 / AddAIBlackList",
        "tool": "—",
        "status": "out_of_scope_write",
    },
    # Activity / Chrono / TimeSheet / Productivity
    {
        "area": "Activity",
        "endpoint": "POST /api/Activity/Overall2",
        "tool": "get_activity_summary",
        "status": "covered_compact",
    },
    {
        "area": "Activity",
        "endpoint": "POST /api/Activity/ActivityWindow|CategoryWindow",
        "tool": "get_activity_detail",
        "status": "covered_compact",
    },
    {
        "area": "Chrono",
        "endpoint": "POST /api/Chrono/Overall2",
        "tool": "get_chrono",
        "status": "covered_compact",
    },
    {
        "area": "TimeSheet",
        "endpoint": "POST /api/TimeSheet/Overall2",
        "tool": "get_timesheet",
        "status": "covered_compact",
    },
    {
        "area": "TimeSheet",
        "endpoint": "SetComment / RemoveComment",
        "tool": "—",
        "status": "out_of_scope_write",
    },
    {
        "area": "Productivity",
        "endpoint": "POST /api/Productivity/Overall3|GetStats",
        "tool": "get_productivity_summary / get_idle_summary",
        "status": "covered_compact",
    },
    {
        "area": "Productivity",
        "endpoint": "DayStructureList / GetDayStructure / GetDashboardMetric1",
        "tool": "get_day_structure / get_dashboard",
        "status": "covered",
    },
    # Analytics / Dashboard
    {
        "area": "Analytics",
        "endpoint": "POST /api/Analytics/Overall|GetDisciplina|GetActivity|GetProductivity",
        "tool": "get_analytics / list_risks(summary)",
        "status": "covered",
    },
    {
        "area": "Dashboard",
        "endpoint": "POST /api/Dashboard/Get*",
        "tool": "get_dashboard",
        "status": "covered_compact",
    },
    # Monitoring
    {
        "area": "Monitoring",
        "endpoint": "POST /api/Monitoring/{19 kinds}",
        "tool": "list_monitoring",
        "status": "covered_compact",
    },
    {
        "area": "Monitoring",
        "endpoint": "Tools → Search fan-out (FilterKey + FilterObjects)",
        "tool": "search_monitoring",
        "status": "covered_compact",
    },
    {
        "area": "Monitoring media",
        "endpoint": "Screenshots/Clipboard/Files/Prints/Webcam Get* binaries",
        "tool": "—",
        "status": "out_of_scope_binary",
    },
    # Live / Stream / VNC
    {
        "area": "Online",
        "endpoint": "POST /api/Live/Overall2",
        "tool": "list_online",
        "status": "covered",
    },
    {
        "area": "Online",
        "endpoint": "Live webcam / LiveStream / VNC / RemoteControl",
        "tool": "—",
        "status": "out_of_scope_binary",
    },
    {
        "area": "Stream",
        "endpoint": "WhichContentExists / GetVideos / GetDownloads",
        "tool": "list_stream_meta",
        "status": "covered",
    },
    {
        "area": "Stream",
        "endpoint": "GetVideoWithSeek / DownloadVideo / ExportVideo",
        "tool": "—",
        "status": "out_of_scope_binary",
    },
    # Account / reports
    {
        "area": "Account",
        "endpoint": "Account/Edit Get* profiles, settings, license, categories",
        "tool": "get_account_readonly",
        "status": "covered",
    },
    {
        "area": "Account",
        "endpoint": "GetUninstallPin1",
        "tool": "—",
        "status": "intentional_skip",
    },
    {
        "area": "Account",
        "endpoint": "Set* / RecalcProductivity / PostCategories / …",
        "tool": "—",
        "status": "out_of_scope_write",
    },
    {
        "area": "Reports",
        "endpoint": "GET GetReports + GetProcessingTasks",
        "tool": "list_reports / get_account_readonly",
        "status": "covered",
    },
    {
        "area": "Reports",
        "endpoint": "QueueReportEmail / SetReports",
        "tool": "—",
        "status": "out_of_scope_write",
    },
    {
        "area": "Users",
        "endpoint": "GetUserData2 / tooltip / group / computer",
        "tool": "get_user_info",
        "status": "covered",
    },
    # Not in current SPA
    {
        "area": "Other",
        "endpoint": "CustomReports / Geo / Archive / legacy XML Overall",
        "tool": "—",
        "status": "out_of_scope_not_in_console",
    },
    {
        "area": "Billing",
        "endpoint": "Pay/*",
        "tool": "—",
        "status": "out_of_scope_write",
    },
]


def coverage_summary() -> dict[str, Any]:
    by_status: dict[str, int] = {}
    for row in COVERAGE:
        by_status[row["status"]] = by_status.get(row["status"], 0) + 1
    return {
        "note": (
            "Read-only MCP coverage of Cloud console APIs. "
            "Writes, binaries, billing, and Help-only endpoints are intentional gaps. "
            "See docs/API.md for the full matrix."
        ),
        "counts_by_status": by_status,
        "rows": COVERAGE,
    }
