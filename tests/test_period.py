"""Offline period resolution tests."""

from __future__ import annotations

from datetime import datetime

import pytest

from octowatch_mcp.period import parse_datetime, resolve_named_period, resolve_tool_period


def test_date_only_same_day_covers_full_day() -> None:
    start, end = resolve_tool_period(date_from="2026-08-26", date_to="2026-08-26")
    assert start == datetime(2026, 8, 26, 0, 0, 0)
    assert end == datetime(2026, 8, 26, 23, 59, 59)


def test_explicit_times_preserved() -> None:
    start, end = resolve_tool_period(
        date_from="2026-08-26 08:00:00",
        date_to="2026-08-26 18:00:00",
    )
    assert start == datetime(2026, 8, 26, 8, 0, 0)
    assert end == datetime(2026, 8, 26, 18, 0, 0)


def test_period_yesterday() -> None:
    now = datetime(2026, 8, 27, 11, 0, 0)
    start, end = resolve_named_period("yesterday", now=now)
    assert start == datetime(2026, 8, 26, 0, 0, 0)
    assert end == datetime(2026, 8, 26, 23, 59, 59)


def test_period_last_7_days() -> None:
    now = datetime(2026, 8, 27, 11, 0, 0)
    start, end = resolve_tool_period(period="last_7_days", now=now)
    assert start == datetime(2026, 8, 21, 0, 0, 0)
    assert end == datetime(2026, 8, 27, 23, 59, 59)


def test_period_wins_over_dates() -> None:
    now = datetime(2026, 8, 27, 11, 0, 0)
    start, end = resolve_tool_period(
        period="today",
        date_from="2020-01-01",
        date_to="2020-01-02",
        now=now,
    )
    assert start == datetime(2026, 8, 27, 0, 0, 0)
    assert end == datetime(2026, 8, 27, 23, 59, 59)


def test_parse_datetime_end_of_day() -> None:
    assert parse_datetime("2026-08-26", end_of_day=True) == datetime(2026, 8, 26, 23, 59, 59)
    assert parse_datetime("2026-08-26", end_of_day=False) == datetime(2026, 8, 26, 0, 0, 0)


def test_invalid_period() -> None:
    with pytest.raises(ValueError, match="Unknown period"):
        resolve_named_period("last_week")
