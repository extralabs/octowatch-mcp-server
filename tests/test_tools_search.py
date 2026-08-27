"""Offline tests for Tools Search fan-out shaping."""

from __future__ import annotations

from datetime import datetime

from octowatch_mcp.tools_search import (
    execute_tools_search,
    resolve_search_kinds,
    shape_search_row,
)


def test_resolve_kinds_aliases() -> None:
    specs = resolve_search_kinds(["sites", "Mail", "clipboard"])
    names = [k for k, _, _ in specs]
    assert names == ["Sites", "Clipboard1", "Mail"]


def test_resolve_kinds_unknown_raises() -> None:
    try:
        resolve_search_kinds(["NotARealKind"])
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_shape_search_row_truncates() -> None:
    row = shape_search_row(
        "Keystrokes",
        {
            "AliasID": 4,
            "AliasName": "Emily",
            "DateTimeValue": "2026-08-26T10:00:00",
            "Activity": "notepad",
            "Text": "x" * 500,
        },
        ("Activity", "Text"),
    )
    assert row["source"] == "Keystrokes"
    assert row["alias_id"] == 4
    assert "…" in row["details"]


def test_execute_tools_search_merges_and_sorts() -> None:
    calls: list[str] = []

    def fake_fetch(kind: str, **kwargs):
        calls.append(kind)
        assert kwargs["filter_key"] == "secret"
        assert kwargs.get("filter_objects") is not None or kind in (
            "Installs",
            "NetworkInterfaces",
        )
        # Later times for Apps so sort puts Apps first
        stamp = "2026-08-27T12:00:00" if kind == "Apps" else "2026-08-26T09:00:00"
        return {
            "TotalRecords": 1,
            "StartFrom": 0,
            "NumRecords": 1,
            "List": [
                {
                    "AliasID": 1,
                    "AliasName": "A",
                    "DateTime": stamp,
                    "DateTimeValue": stamp,
                    "Name": kind,
                    "URL": "http://x",
                    "WindowTitle": "wt",
                    "Activity": kind,
                    "Text": "t",
                    "ClipboardText": "c",
                    "Body": "b",
                    "Sender": "s",
                    "Recipient": "r",
                    "SrcPath": "/f",
                    "ProcessName": "p",
                    "DocumentName": "d",
                    "Printer": "pr",
                    "Version": "1",
                    "Publisher": "pub",
                    "IPs": "1.1.1.1",
                    "Description": "desc",
                    "AppExe": "exe",
                    "RecognitionResult": "ocr",
                }
            ],
        }

    out = execute_tools_search(
        fake_fetch,
        filter_key="secret",
        date_from=datetime(2026, 8, 26),
        date_to=datetime(2026, 8, 27, 23, 59, 59),
        users_filter=[{"NodeType": -666666, "UserID": -666666}],
        kinds=["Sites", "Apps"],
        per_source_limit=5,
        max_rows=10,
    )
    assert set(calls) == {"Sites", "Apps"}
    assert out["row_count"] == 2
    assert out["rows"][0]["source"] == "Apps"
    assert all(s["ok"] for s in out["sources"])


def test_execute_tools_search_requires_key() -> None:
    try:
        execute_tools_search(
            lambda *a, **k: {},
            filter_key="  ",
            date_from=None,
            date_to=None,
            users_filter=None,
        )
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
