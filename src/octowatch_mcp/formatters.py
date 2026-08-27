"""Pure formatters: compact MCP responses for agents."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

RISK_SLIM_KEEP = (
    "ID",
    "AliasName",
    "AliasID",
    "DateTime",
    "RuleType",
    "RuleName2",
    "RuleName",
    "Keyword",
    "ActivityObject",
    "Hidden",
    "RiskCount",
)


def seconds_hms(sec: float | None) -> str:
    sec = int(sec or 0)
    sign = "-" if sec < 0 else ""
    sec = abs(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{sign}{h}h {m:02d}m"
    if m:
        return f"{sign}{m}m {s:02d}s"
    return f"{sign}{s}s"


def slim_risk_row(row: dict[str, Any]) -> dict[str, Any]:
    return {k: row.get(k) for k in RISK_SLIM_KEEP if row.get(k) is not None}


def filter_by_alias_id(rows: list[Any], user_id: int | None) -> list[Any]:
    if user_id is None:
        return rows
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("AliasID") == user_id or row.get("ID") == user_id:
            out.append(row)
    return out


def summarize_risks_page(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_rule: Counter[str] = Counter()
    by_day: Counter[str] = Counter()
    for row in items:
        rule = row.get("RuleName2") or row.get("RuleName") or "unknown"
        by_rule[str(rule)] += 1
        dt = str(row.get("DateTime") or "")[:10]
        if dt:
            by_day[dt] += 1
    return {
        "by_rule": [{"rule_name": k, "count": v} for k, v in by_rule.most_common()],
        "by_day": [{"day": k, "count": v} for k, v in sorted(by_day.items())],
        "sample": [slim_risk_row(r) for r in items[:10]],
    }


def analytics_risks_by_user(
    analytics_risks: list[dict[str, Any]] | None,
    *,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    rows = []
    for r in analytics_risks or []:
        aid = r.get("ID")
        if user_id is not None and aid != user_id:
            continue
        rows.append(
            {
                "alias_name": r.get("Name"),
                "alias_id": aid,
                "count": int(r.get("Value") or 0),
            }
        )
    rows.sort(key=lambda x: -x["count"])
    return rows


def format_activity_top(
    data: dict[str, Any],
    *,
    top_n: int = 15,
    user_id: int | None = None,
) -> dict[str, Any]:
    items = data.get("List") or []
    if user_id is not None:
        # Activity Overall2 is usually aggregated apps/sites, not per-user rows.
        # Keep as-is when no AliasID; filter if present.
        filtered = [i for i in items if isinstance(i, dict) and i.get("AliasID") in (None, user_id)]
        if any(isinstance(i, dict) and i.get("AliasID") is not None for i in items):
            items = [i for i in items if isinstance(i, dict) and i.get("AliasID") == user_id]
        else:
            items = filtered if filtered else items

    apps: list[dict[str, Any]] = []
    sites: list[dict[str, Any]] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        entry = {
            "name": row.get("Name") or row.get("AppExe") or row.get("URL"),
            "active_sec": int(row.get("ActiveTime") or 0),
            "active_hms": seconds_hms(row.get("ActiveTime")),
            "inactive_sec": int(row.get("InactiveTime") or 0),
            "category": (row.get("Category") or {}).get("Name")
            if isinstance(row.get("Category"), dict)
            else None,
        }
        if row.get("IsWebsite"):
            sites.append(entry)
        else:
            apps.append(entry)
    apps.sort(key=lambda x: -x["active_sec"])
    sites.sort(key=lambda x: -x["active_sec"])
    return {
        "apps": apps[:top_n],
        "sites": sites[:top_n],
        "total_apps": len(apps),
        "total_sites": len(sites),
    }


def format_productivity_rollup(
    detail: dict[str, Any] | None,
    stats: dict[str, Any] | None,
    analytics: dict[str, Any] | None,
    *,
    user_id: int | None = None,
) -> dict[str, Any]:
    by: dict[Any, dict[str, Any]] = defaultdict(
        lambda: {
            "alias_name": None,
            "alias_id": None,
            "productive_sec": 0,
            "neutral_sec": 0,
            "unproductive_sec": 0,
            "active_sec": 0,
            "inactive_sec": 0,
            "days": set(),
        }
    )

    for row in (detail or {}).get("List") or []:
        if not isinstance(row, dict):
            continue
        aid = row.get("AliasID")
        if user_id is not None and aid != user_id:
            continue
        b = by[aid]
        b["alias_id"] = aid
        b["alias_name"] = row.get("AliasName")
        b["productive_sec"] += int(row.get("ProductiveTime") or 0)
        b["neutral_sec"] += int(row.get("NeutralTime") or 0)
        b["unproductive_sec"] += int(row.get("UnproductiveTime") or 0)
        b["active_sec"] += int(row.get("ActiveTime") or 0)
        b["inactive_sec"] += int(row.get("InactiveTime") or 0)
        d = str(row.get("DateTimeValue") or row.get("ColGroup") or "")[:10]
        if d and d != "0001-01-01":
            b["days"].add(d)

    # Prefer stats InactiveTime if detail lacked it
    for row in (stats or {}).get("List") or []:
        if not isinstance(row, dict):
            continue
        aid = row.get("AliasID")
        if user_id is not None and aid != user_id:
            continue
        b = by[aid]
        b["alias_id"] = aid
        b["alias_name"] = b["alias_name"] or row.get("AliasName")
        inactive = int(row.get("InactiveTime") or 0)
        if inactive and not b["inactive_sec"]:
            b["inactive_sec"] = inactive

    users = []
    for b in by.values():
        active = b["active_sec"] or 0
        users.append(
            {
                "alias_name": b["alias_name"],
                "alias_id": b["alias_id"],
                "days": len(b["days"]),
                "active_sec": active,
                "active_hms": seconds_hms(active),
                "productive_sec": b["productive_sec"],
                "productive_hms": seconds_hms(b["productive_sec"]),
                "productive_pct": round(100.0 * b["productive_sec"] / active, 1) if active else 0.0,
                "neutral_sec": b["neutral_sec"],
                "neutral_hms": seconds_hms(b["neutral_sec"]),
                "unproductive_sec": b["unproductive_sec"],
                "unproductive_hms": seconds_hms(b["unproductive_sec"]),
                "inactive_sec": b["inactive_sec"],
                "inactive_hms": seconds_hms(b["inactive_sec"]),
            }
        )
    users.sort(key=lambda x: -x["active_sec"])

    metrics = (analytics or {}).get("Metrics") if isinstance(analytics, dict) else None
    top_risks = analytics_risks_by_user(
        (analytics or {}).get("Risks") if isinstance(analytics, dict) else None,
        user_id=user_id,
    )
    return {
        "users": users,
        "analytics_metrics": metrics,
        "top_risks": top_risks,
    }


def format_idle_summary(
    detail: dict[str, Any] | None,
    *,
    user_id: int | None = None,
    min_idle_hours: float | None = None,
) -> dict[str, Any]:
    by: dict[Any, dict[str, Any]] = defaultdict(
        lambda: {"alias_name": None, "alias_id": None, "inactive_sec": 0, "active_sec": 0}
    )
    for row in (detail or {}).get("List") or []:
        if not isinstance(row, dict):
            continue
        aid = row.get("AliasID")
        if user_id is not None and aid != user_id:
            continue
        b = by[aid]
        b["alias_id"] = aid
        b["alias_name"] = row.get("AliasName")
        b["inactive_sec"] += int(row.get("InactiveTime") or 0)
        b["active_sec"] += int(row.get("ActiveTime") or 0)

    min_sec = int((min_idle_hours or 0) * 3600)
    users = []
    for b in by.values():
        if b["inactive_sec"] < min_sec:
            continue
        users.append(
            {
                "alias_name": b["alias_name"],
                "alias_id": b["alias_id"],
                "inactive_sec": b["inactive_sec"],
                "inactive_hms": seconds_hms(b["inactive_sec"]),
                "active_sec": b["active_sec"],
                "active_hms": seconds_hms(b["active_sec"]),
            }
        )
    users.sort(key=lambda x: -x["inactive_sec"])
    return {
        "note": (
            "Idle here is InactiveTime from productivity (not Alerts/Anomalies). "
            "Use list_anomalies for formal deviation alerts."
        ),
        "users": users,
    }


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", ""))
    except ValueError:
        return None


def format_timesheet(
    data: dict[str, Any],
    *,
    user_id: int | None = None,
) -> dict[str, Any]:
    users_out = []
    for u in data.get("Users") or []:
        if not isinstance(u, dict):
            continue
        aid = u.get("AliasID")
        if user_id is not None and aid != user_id:
            continue
        settings = u.get("Settings") or {}
        days = []
        for day in u.get("List") or []:
            if not isinstance(day, dict):
                continue
            tf = _parse_iso(day.get("TimeFrom"))
            tt = _parse_iso(day.get("TimeTo"))
            worked = None
            if tf and tt:
                worked = int((tt - tf).total_seconds())
                if worked < 0:
                    worked += 24 * 3600
            date_val = str(day.get("DateValue") or "")[:10]
            expected_h = None
            if tf:
                # Day1=Monday … Day7=Sunday (OctoWatch timetable convention)
                day_idx = tf.weekday() + 1
                expected_h = settings.get(f"Day{day_idx}Hours")
            days.append(
                {
                    "date": date_val,
                    "from": (day.get("TimeFrom") or "")[11:19] or None,
                    "to": (day.get("TimeTo") or "")[11:19] or None,
                    "worked_sec": worked,
                    "worked_hms": seconds_hms(worked) if worked is not None else None,
                    "expected_hours": expected_h,
                    "fix_hours": day.get("FixHours"),
                    "comment": day.get("Comment"),
                }
            )
        users_out.append(
            {
                "alias_name": u.get("AliasName"),
                "alias_id": aid,
                "profile": settings.get("ProfileName"),
                "allowed_delay_min": settings.get("AllowedDelay"),
                "days": days,
            }
        )
    return {"users": users_out}
