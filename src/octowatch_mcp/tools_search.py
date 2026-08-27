"""Tools Search fan-out — same Monitoring kinds + FilterObjects as the web console.

Console: Tools → Search (toolsSearchApi.executeToolsSearch). Parallel POSTs to
Monitoring/* with FilterKey + per-kind FilterObjects; merge and sort by time.
Does not call SearchQueries or Risks.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

# (Monitoring kind, default FilterObjects, detail field candidates)
SEARCH_KIND_SPECS: list[tuple[str, str | None, tuple[str, ...]]] = [
    ("Sites", "url,wt", ("URL", "WindowTitle")),
    ("Apps", "app,wt", ("Name", "WindowTitle")),
    ("Keystrokes", "app,keystrokestext", ("Activity", "Text")),
    ("Clipboard1", "app,clipboardtext", ("Activity", "ClipboardText")),
    (
        "Screens",
        "ocr,url,wt",
        ("Activity", "AppExeOrURL", "AppExe", "WindowTitle", "RecognitionResult"),
    ),
    ("Messengers", "chatstext", ("Body", "Text", "Sender", "Recipient")),
    (
        "Mail",
        "chatstext,sender,recipient,subject",
        ("Text", "Body", "Sender", "Recipient", "Subject"),
    ),
    ("WebcamAudio", "ar,wt", ("WindowTitle", "RecognitionResult")),
    ("Files", "files_file", ("SrcPath", "ProcessName", "Name")),
    ("Prints", "prints_file", ("DocumentName", "Printer")),
    ("Installs", None, ("Name", "Version", "Publisher")),
    ("NetworkInterfaces", None, ("Name", "IPs", "Description")),
    ("WebForms", "url", ("URL", "AppExe")),
]

SEARCH_KINDS = frozenset(k for k, _, _ in SEARCH_KIND_SPECS)

# SPA ToolsSearchSource names → Monitoring action
SOURCE_ALIASES: dict[str, str] = {
    "sites": "Sites",
    "apps": "Apps",
    "keystrokes": "Keystrokes",
    "clipboard": "Clipboard1",
    "clipboard1": "Clipboard1",
    "screens": "Screens",
    "messengers": "Messengers",
    "mail": "Mail",
    "webcam": "WebcamAudio",
    "webcamaudio": "WebcamAudio",
    "files": "Files",
    "prints": "Prints",
    "installs": "Installs",
    "networkinterfaces": "NetworkInterfaces",
    "network": "NetworkInterfaces",
    "webforms": "WebForms",
}


def resolve_search_kinds(kinds: list[str] | None) -> list[tuple[str, str | None, tuple[str, ...]]]:
    if not kinds:
        return list(SEARCH_KIND_SPECS)
    wanted: set[str] = set()
    unknown: list[str] = []
    for raw in kinds:
        token = (raw or "").strip()
        if not token:
            continue
        mapped = SOURCE_ALIASES.get(token.lower(), token)
        if mapped in SEARCH_KINDS:
            wanted.add(mapped)
        else:
            unknown.append(token)
    if unknown or not wanted:
        raise ValueError(
            "Unknown or empty search kinds "
            f"{unknown or kinds!r}; valid: {sorted(SEARCH_KINDS)} "
            f"(aliases: {sorted(SOURCE_ALIASES)})"
        )
    return [spec for spec in SEARCH_KIND_SPECS if spec[0] in wanted]


def _row_time(row: dict[str, Any]) -> str:
    return str(row.get("DateTime") or row.get("DateTimeValue") or "")


def _details(row: dict[str, Any], fields: tuple[str, ...], text_max: int = 200) -> str:
    parts: list[str] = []
    for key in fields:
        val = row.get(key)
        if val is None or val == "":
            continue
        s = str(val).strip()
        if not s:
            continue
        if len(s) > text_max:
            s = s[:text_max] + "…"
        parts.append(s)
    # WebForms Fields array
    fields_arr = row.get("Fields")
    if isinstance(fields_arr, list):
        bits = []
        for f in fields_arr[:4]:
            if isinstance(f, dict):
                bits.append("=".join(str(x) for x in (f.get("Name"), f.get("Value")) if x))
        if bits:
            parts.append("; ".join(bits))
    return " · ".join(parts)


def shape_search_row(kind: str, row: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "source": kind,
        "date_time": _row_time(row) or None,
        "alias_id": row.get("AliasID"),
        "alias_name": row.get("AliasName"),
        "details": _details(row, fields),
    }
    if kind == "Screens" and row.get("ID") is not None:
        out["screen_id"] = row.get("ID")
    return out


def execute_tools_search(
    fetch_kind: Callable[..., Any],
    *,
    filter_key: str,
    date_from: datetime | None,
    date_to: datetime | None,
    users_filter: list[dict[str, int]] | None,
    offset: int = 0,
    per_source_limit: int = 20,
    max_rows: int = 50,
    kinds: list[str] | None = None,
    max_workers: int = 8,
) -> dict[str, Any]:
    """Run parallel Monitoring searches; merge/sort like the console Tools Search."""
    fk = (filter_key or "").strip()
    if not fk:
        raise ValueError("filter_key is required for tools search")

    specs = resolve_search_kinds(kinds)
    per_source_limit = max(1, min(int(per_source_limit), 100))
    max_rows = max(1, min(int(max_rows), 200))
    offset = max(0, int(offset))

    sources_meta: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    def _one(kind: str, filter_objects: str | None, fields: tuple[str, ...]) -> dict[str, Any]:
        data = fetch_kind(
            kind,
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
            offset=offset,
            num_rows=per_source_limit,
            filter_key=fk,
            filter_objects=filter_objects,
            videos=False,
            screens=True,
        )
        items = []
        total = start = num = None
        if isinstance(data, dict):
            total = data.get("TotalRecords")
            start = data.get("StartFrom")
            num = data.get("NumRecords")
            for raw in data.get("List") or []:
                if isinstance(raw, dict):
                    items.append(shape_search_row(kind, raw, fields))
        return {
            "source": kind,
            "ok": True,
            "error": None,
            "total_records": total,
            "start_from": start,
            "num_records": num if num is not None else len(items),
            "filter_objects": filter_objects,
            "rows": items,
        }

    with ThreadPoolExecutor(max_workers=min(max_workers, len(specs) or 1)) as pool:
        futures = {pool.submit(_one, kind, fo, fields): kind for kind, fo, fields in specs}
        for fut in as_completed(futures):
            kind = futures[fut]
            try:
                result = fut.result()
                rows.extend(result.pop("rows"))
                sources_meta.append(result)
            except Exception as exc:  # noqa: BLE001 — per-source errors must not fail all
                sources_meta.append(
                    {
                        "source": kind,
                        "ok": False,
                        "error": str(exc),
                        "total_records": None,
                        "start_from": None,
                        "num_records": None,
                        "filter_objects": next((fo for k, fo, _ in specs if k == kind), None),
                    }
                )

    sources_meta.sort(key=lambda s: s["source"])
    rows.sort(key=lambda r: str(r.get("date_time") or ""), reverse=True)
    truncated = len(rows) > max_rows
    rows = rows[:max_rows]

    can_next = False
    for s in sources_meta:
        if not s.get("ok"):
            continue
        try:
            total = int(s["total_records"])
            start = int(s["start_from"])
            num = int(s["num_records"])
        except (TypeError, ValueError, KeyError):
            continue
        if start + num < total:
            can_next = True
            break

    return {
        "filter_key": fk,
        "offset": offset,
        "per_source_limit": per_source_limit,
        "rows": rows,
        "row_count": len(rows),
        "truncated": truncated,
        "can_next_page": can_next,
        "sources": sources_meta,
        "note": (
            "Fan-out matches console Tools → Search (not SearchQueries/Risks). "
            "Sensitive text is truncated in details."
        ),
    }
