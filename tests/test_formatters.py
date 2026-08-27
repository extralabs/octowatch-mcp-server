"""Offline formatter tests."""

from __future__ import annotations

from octowatch_mcp.formatters import (
    analytics_risks_by_user,
    filter_by_alias_id,
    format_activity_top,
    format_idle_summary,
    format_productivity_rollup,
    format_timesheet,
    seconds_hms,
    summarize_risks_page,
)
from octowatch_mcp.report_types import label_report_types


def test_filter_by_alias_id_ignores_event_id() -> None:
    rows = [
        {"ID": 8, "AliasID": 10, "AliasName": "JULIAN"},
        {"ID": 22615, "AliasID": 8, "AliasName": "Pc abajo"},
    ]
    # Must not match risk/event ID=8 — only AliasID=8
    out = filter_by_alias_id(rows, 8)
    assert len(out) == 1
    assert out[0]["AliasName"] == "Pc abajo"


def test_seconds_hms() -> None:
    assert seconds_hms(3661) == "1h 01m"
    assert seconds_hms(65) == "1m 05s"


def test_summarize_risks_page() -> None:
    items = [
        {
            "AliasName": "A",
            "AliasID": 1,
            "DateTime": "2026-08-26T10:00:00",
            "RuleName2": "Adult content",
            "Keyword": "x",
        },
        {
            "AliasName": "B",
            "AliasID": 2,
            "DateTime": "2026-08-26T11:00:00",
            "RuleName2": "Adult content",
            "Keyword": "y",
        },
        {
            "AliasName": "A",
            "AliasID": 1,
            "DateTime": "2026-08-25T09:00:00",
            "RuleName2": "USB",
            "Keyword": "z",
        },
    ]
    meta = summarize_risks_page(items)
    assert meta["by_rule"][0] == {"rule_name": "Adult content", "count": 2}
    assert {"day": "2026-08-26", "count": 2} in meta["by_day"]
    assert len(meta["sample"]) == 3


def test_analytics_risks_by_user() -> None:
    rows = analytics_risks_by_user(
        [
            {"Name": "JULIAN", "ID": 10, "Value": 558},
            {"Name": "Wilmer", "ID": 11, "Value": 456},
        ]
    )
    assert rows[0]["count"] == 558
    assert (
        analytics_risks_by_user(
            [{"Name": "JULIAN", "ID": 10, "Value": 558}],
            user_id=11,
        )
        == []
    )


def test_format_activity_top() -> None:
    data = {
        "List": [
            {"Name": "Rhino", "IsWebsite": False, "ActiveTime": 1000},
            {"Name": "google.com", "IsWebsite": True, "ActiveTime": 50, "URL": "google.com"},
            {"Name": "Excel", "IsWebsite": False, "ActiveTime": 20},
        ]
    }
    out = format_activity_top(data, top_n=2)
    assert len(out["apps"]) == 2
    assert out["apps"][0]["name"] == "Rhino"
    assert out["sites"][0]["name"] == "google.com"


def test_format_idle_and_productivity() -> None:
    detail = {
        "List": [
            {
                "AliasName": "A",
                "AliasID": 1,
                "ProductiveTime": 100,
                "NeutralTime": 10,
                "UnproductiveTime": 5,
                "ActiveTime": 115,
                "InactiveTime": 500,
                "DateTimeValue": "2026-08-26T00:00:00",
            },
            {
                "AliasName": "B",
                "AliasID": 2,
                "ProductiveTime": 50,
                "NeutralTime": 0,
                "UnproductiveTime": 0,
                "ActiveTime": 50,
                "InactiveTime": 9000,
                "DateTimeValue": "2026-08-26T00:00:00",
            },
        ]
    }
    idle = format_idle_summary(detail, min_idle_hours=1)
    assert idle["users"][0]["alias_id"] == 2
    assert len(idle["users"]) == 1

    rollup = format_productivity_rollup(detail, {"List": []}, {"Metrics": {}, "Risks": []})
    assert rollup["users"][0]["alias_id"] == 1
    assert rollup["users"][0]["productive_pct"] > 0


def test_format_timesheet() -> None:
    data = {
        "Users": [
            {
                "AliasName": "Wilmer",
                "AliasID": 11,
                "Settings": {"ProfileName": "Custom", "AllowedDelay": 15, "Day3Hours": 24},
                "List": [
                    {
                        "DateValue": "2026-08-26T00:00:00",
                        "TimeFrom": "2026-08-26T06:05:00",
                        "TimeTo": "2026-08-26T17:55:00",
                        "FixHours": None,
                        "Comment": None,
                    }
                ],
            }
        ]
    }
    out = format_timesheet(data)
    day = out["users"][0]["days"][0]
    assert day["from"] == "06:05:00"
    assert day["worked_sec"] == 11 * 3600 + 50 * 60
    assert day["expected_hours"] == 24


def test_report_type_labels() -> None:
    labeled = label_report_types([24, 4, 999])
    assert labeled[0]["label"] == "Risks"
    assert labeled[2]["label"] == "Type 999"
