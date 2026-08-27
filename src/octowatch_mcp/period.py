"""Period / datetime helpers for OctoWatch API (local-naive DateFrom/DateTo)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

DATE_FMT = "%Y-%m-%d %H:%M:%S"

PeriodName = Literal["today", "yesterday", "last_7_days", "last_30_days"]
VALID_PERIODS = frozenset({"today", "yesterday", "last_7_days", "last_30_days"})


def _local_now() -> datetime:
    return datetime.now().astimezone().replace(tzinfo=None, microsecond=0)


def parse_datetime(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    """Parse API-style datetime. Date-only → start or end of that calendar day."""
    if not value:
        return None
    value = value.strip()
    for fmt in (DATE_FMT, "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)  # noqa: DTZ007
            if fmt == "%Y-%m-%d":
                if end_of_day:
                    return dt.replace(hour=23, minute=59, second=59)
                return dt.replace(hour=0, minute=0, second=0)
            return dt
        except ValueError:
            continue
    raise ValueError(
        f"Invalid datetime '{value}'. Use 'YYYY-MM-DD', "
        f"'YYYY-MM-DD HH:MM:SS', or period=today|yesterday|last_7_days|last_30_days."
    )


def resolve_named_period(period: str, *, now: datetime | None = None) -> tuple[datetime, datetime]:
    period = period.strip().lower()
    if period not in VALID_PERIODS:
        raise ValueError(
            f"Unknown period '{period}'. Use: today, yesterday, last_7_days, last_30_days."
        )
    now = now or _local_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=0)

    if period == "today":
        return today_start, today_end
    if period == "yesterday":
        y = today_start - timedelta(days=1)
        return y, y.replace(hour=23, minute=59, second=59)
    if period == "last_7_days":
        start = today_start - timedelta(days=6)
        return start, today_end
    # last_30_days
    start = today_start - timedelta(days=29)
    return start, today_end


def resolve_tool_period(
    *,
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    default_days: int = 1,
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Resolve MCP tool period args to DateFrom/DateTo.

    If ``period`` is set, it wins over date_from/date_to.
    Date-only date_to becomes end of that day (23:59:59).
    """
    if period:
        return resolve_named_period(period, now=now)

    start = parse_datetime(date_from, end_of_day=False)
    end = parse_datetime(date_to, end_of_day=True)

    now = now or _local_now()
    if end is None:
        end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    if start is None:
        start = (end - timedelta(days=default_days)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    if start > end:
        raise ValueError(f"date_from ({start}) is after date_to ({end})")
    return start, end


def resolve_period(
    date_from: datetime | None,
    date_to: datetime | None,
    default_days: int,
) -> tuple[datetime, datetime]:
    """Fill missing bounds for already-parsed datetimes (client layer)."""
    end = date_to or _local_now().replace(hour=23, minute=59, second=59, microsecond=0)
    start = date_from or (end - timedelta(days=default_days)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return start, end
