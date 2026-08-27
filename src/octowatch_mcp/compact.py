"""Payload guards: strip blobs, truncate long text, cap list length."""

from __future__ import annotations

from typing import Any

BLOB_KEY_FRAGMENTS = (
    "thumbnail",
    "screenshot",
    "image",
    "bitmap",
    "binary",
    "photo",
    "frame",
    "base64",
    "contentbytes",
    "filebytes",
    "rawdata",
    "icondata",
)

TEXT_KEYS = (
    "Text",
    "Body",
    "Message",
    "Content",
    "OCR",
    "OcrText",
    "Keystrokes",
    "ClipboardText",
    "Keyword",
    "ActivityObject",
    "Document",
    "Subject",
    "Preview",
)

DEFAULT_TEXT_MAX = 400
DEFAULT_LIST_CAP = 100


def _is_blob_key(key: str) -> bool:
    low = key.lower().replace("_", "")
    return any(frag in low for frag in BLOB_KEY_FRAGMENTS)


def compact_value(
    value: Any,
    *,
    text_max: int = DEFAULT_TEXT_MAX,
    depth: int = 0,
) -> Any:
    if depth > 8:
        return "…"
    if isinstance(value, str):
        if len(value) > text_max:
            return value[:text_max] + f"…(+{len(value) - text_max})"
        # Heuristic: long base64-ish
        if len(value) > 200 and value[:20].isalnum() and "/" not in value[:40]:
            return f"[omitted {len(value)} chars]"
        return value
    if isinstance(value, list):
        return [compact_value(v, text_max=text_max, depth=depth + 1) for v in value]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if _is_blob_key(str(k)):
                if v is None or v == "" or v is False:
                    continue
                out[str(k)] = "[omitted binary/blob]"
                continue
            if str(k) in TEXT_KEYS and isinstance(v, str) and len(v) > text_max:
                out[str(k)] = v[:text_max] + f"…(+{len(v) - text_max})"
            else:
                out[str(k)] = compact_value(v, text_max=text_max, depth=depth + 1)
        return out
    return value


def compact_api_payload(
    data: Any,
    *,
    list_cap: int = DEFAULT_LIST_CAP,
    text_max: int = DEFAULT_TEXT_MAX,
) -> Any:
    """Compact Overall2-style {List, TotalRecords, …} or arbitrary JSON."""
    if not isinstance(data, dict):
        return compact_value(data, text_max=text_max)

    out = dict(data)
    for list_key in ("List", "Users", "Items", "Alerts", "Listview"):
        rows = out.get(list_key)
        if isinstance(rows, list) and len(rows) > list_cap:
            out[list_key] = rows[:list_cap]
            out["_truncated"] = True
            out["_original_list_len"] = len(rows)
    return compact_value(out, text_max=text_max)
