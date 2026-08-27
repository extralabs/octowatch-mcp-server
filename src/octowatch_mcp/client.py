"""Thin HTTP client for OctoWatch Cloud REST API.

Auth: GET /api/Access/login-jwt → Bearer Token (+ refresh via PublicID).
Period queries: POST with DateFrom/DateTo headers and UsersGroups JSON body.
Docs UI: https://app.octowatchdlp.com/api/  ·  Host: https://cloud.octowatchdlp.com
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Self
from urllib.parse import quote

import httpx

from octowatch_mcp.config import ROOT_FILTER, Settings, get_settings
from octowatch_mcp.period import DATE_FMT, parse_datetime, resolve_period

__all__ = [
    "DATE_FMT",
    "OctoWatchAPIError",
    "OctoWatchClient",
    "parse_datetime",
    "resolve_period",
    "users_filter_all",
    "users_filter_for_group",
]



class OctoWatchAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class OctoWatchClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._token: str | None = None
        self._refresh_token: str | None = None
        self._public_id: str | None = None
        self._expires_at: float = 0.0
        self._http = httpx.Client(
            base_url=self.settings.api_base,
            timeout=60.0,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # --- auth -----------------------------------------------------------------

    def login(self) -> dict[str, Any]:
        email = quote(self.settings.email, safe="")
        password = quote(self.settings.password, safe="")
        path = f"/api/Access/login-jwt?email={email}&password={password}"
        data = self._request_json("GET", path, auth=False)
        if not data.get("Success") and not data.get("Token"):
            raise OctoWatchAPIError(
                f"login-jwt failed: {data.get('Message') or data}",
                body=str(data),
            )
        self._token = data["Token"]
        self._refresh_token = data.get("RefreshToken")
        self._public_id = str(data.get("PublicID", ""))
        expires_in = int(data.get("ExpiresIn") or 3600)
        self._expires_at = time.time() + max(60, expires_in - 60)
        return data

    def ensure_auth(self) -> None:
        if self._token and time.time() < self._expires_at:
            return
        if self._token and self._refresh_token and self._public_id is not None:
            try:
                self.refresh()
                return
            except OctoWatchAPIError:
                pass
        self.login()

    def refresh(self) -> dict[str, Any]:
        if not self._refresh_token or self._public_id is None:
            raise OctoWatchAPIError("No refresh token; call login() first")
        rt = quote(self._refresh_token, safe="")
        pid = quote(self._public_id, safe="")
        path = f"/api/Access/refresh-token?refresh_Token={rt}&PublicID={pid}"
        data = self._request_json("GET", path, auth=False)
        self._token = data["Token"]
        if data.get("RefreshToken"):
            self._refresh_token = data["RefreshToken"]
        expires_in = int(data.get("ExpiresIn") or 3600)
        self._expires_at = time.time() + max(60, expires_in - 60)
        return data

    # --- low-level ------------------------------------------------------------

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        auth: bool = True,
        headers: dict[str, str] | None = None,
        json_body: Any = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        hdrs = dict(headers or {})
        if auth:
            self.ensure_auth()
            hdrs["Authorization"] = f"Bearer {self._token}"
        response = self._http.request(
            method,
            path,
            headers=hdrs,
            json=json_body,
            params=params,
        )
        if response.status_code == 401 and auth:
            self.login()
            hdrs["Authorization"] = f"Bearer {self._token}"
            response = self._http.request(
                method,
                path,
                headers=hdrs,
                json=json_body,
                params=params,
            )
        if response.status_code >= 400:
            raise OctoWatchAPIError(
                f"{method} {path} → HTTP {response.status_code}: {response.text[:500]}",
                status_code=response.status_code,
                body=response.text,
            )
        if not response.content:
            return None
        try:
            return response.json()
        except (ValueError, TypeError) as exc:
            raise OctoWatchAPIError(
                f"{method} {path}: invalid JSON ({exc})",
                status_code=response.status_code,
                body=response.text[:500],
            ) from exc

    def get(self, path: str, **kwargs: Any) -> Any:
        return self._request_json("GET", path, **kwargs)

    def post(
        self,
        path: str,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
        extra_headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Any:
        df, dt = resolve_period(date_from, date_to, self.settings.default_days)
        headers = {
            "Content-Type": "application/json",
            "DateFrom": df.strftime(DATE_FMT),
            "DateTo": dt.strftime(DATE_FMT),
            "Offset": "0",
            "NumRows": "500",
            "HideHidden": "False",
        }
        if extra_headers:
            headers.update(extra_headers)
        body = users_filter if users_filter is not None else list(ROOT_FILTER)
        return self._request_json("POST", path, headers=headers, json_body=body, **kwargs)

    # --- read-only resources --------------------------------------------------

    def get_users_groups(self) -> Any:
        return self.get("/api/Edit/GetUsersGroups2")

    def get_users(self) -> Any:
        return self.get("/api/Edit/GetUsers")

    def get_groups(self) -> Any:
        return self.get("/api/Edit/GetGroups")

    def get_reports_settings(self) -> Any:
        """Scheduled report mailing settings (may be empty on demo)."""
        return self.get("/api/Account/GetReports")

    def get_processing_tasks(self) -> Any:
        return self.get("/api/Edit/GetProcessingTasks")

    def risks(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
        offset: int = 0,
        num_rows: int = 100,
    ) -> Any:
        return self.post(
            "/api/Risks/Overall2",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
            extra_headers={"Offset": str(offset), "NumRows": str(num_rows)},
        )

    def risks_pages(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
        page_size: int = 500,
        max_rows: int = 2000,
    ) -> dict[str, Any]:
        """Fetch Risks/Overall2 pages until done or max_rows."""
        page_size = max(1, min(page_size, 500))
        offset = 0
        merged: list[Any] = []
        total = None
        while offset < max_rows:
            chunk = self.risks(
                date_from=date_from,
                date_to=date_to,
                users_filter=users_filter,
                offset=offset,
                num_rows=min(page_size, max_rows - offset),
            )
            if not isinstance(chunk, dict):
                break
            if total is None:
                total = int(chunk.get("TotalRecords") or 0)
            rows = chunk.get("List") or []
            merged.extend(rows)
            if not rows or len(merged) >= (total or 0) or len(rows) < page_size:
                break
            offset += len(rows)
        return {
            "List": merged,
            "TotalRecords": total if total is not None else len(merged),
            "StartFrom": 0,
            "NumRecords": len(merged),
            "capped": bool(total is not None and len(merged) < total),
        }

    def anomalies(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
        offset: int = 0,
        num_rows: int = 100,
        filter_key: str | None = None,
    ) -> Any:
        extra = {"Offset": str(offset), "NumRows": str(num_rows)}
        if filter_key:
            extra["FilterKey"] = quote(filter_key, safe="")
        return self.post(
            "/api/Alerts/Overall2",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
            extra_headers=extra,
        )

    def activity(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
    ) -> Any:
        return self.post(
            "/api/Activity/Overall2",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
        )

    def timesheet(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
    ) -> Any:
        return self.post(
            "/api/TimeSheet/Overall2",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
        )

    def productivity(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
    ) -> Any:
        return self.post(
            "/api/Productivity/Overall3",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
        )

    def productivity_stats(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
    ) -> Any:
        return self.post(
            "/api/Productivity/GetStats",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
        )

    def analytics_summary(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
    ) -> Any:
        return self.post(
            "/api/Analytics/Overall",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
        )


def users_filter_for_group(group_id: int) -> list[dict[str, int]]:
    """Filter by group node (NodeType=1)."""
    return [{"NodeType": 1, "UserID": group_id}]


def users_filter_all() -> list[dict[str, int]]:
    return list(ROOT_FILTER)
