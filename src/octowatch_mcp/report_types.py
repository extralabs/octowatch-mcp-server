"""Public console report-type labels (read-only MCP enrichment)."""

from __future__ import annotations

# Codes observed in Cloud console / public API docs UI naming.
REPORT_TYPE_LABELS: dict[int, str] = {
    1: "Analytics",
    4: "Productivity",
    8: "Activity",
    10: "Chronometry",
    12: "Timesheet",
    13: "Day structure",
    14: "Keystrokes",
    20: "Sites & applications",
    24: "Risks",
    27: "Alerts / deviations",
    28: "Time by days",
    39: "Screenshots report",
    40: "Video report",
}


def label_report_types(types: list[int] | None) -> list[dict[str, int | str]]:
    out: list[dict[str, int | str]] = []
    for code in types or []:
        try:
            n = int(code)
        except (TypeError, ValueError):
            continue
        out.append({"id": n, "label": REPORT_TYPE_LABELS.get(n, f"Type {n}")})
    return out
