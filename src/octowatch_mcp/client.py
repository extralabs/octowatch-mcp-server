"""Thin HTTP client for OctoWatch Cloud REST API.

Auth: GET /api/Access/login-jwt → Bearer Token (+ refresh via PublicID).
Period queries: POST with DateFrom/DateTo headers and TreeviewUsers JSON body.
Docs UI: https://app.octowatchdlp.com/api/  ·  Host: https://cloud.octowatchdlp.com
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any, Self
from urllib.parse import quote

import httpx

from octowatch_mcp.config import Settings, get_settings
from octowatch_mcp.filters import (
    build_users_filter,
    users_filter_all,
    users_filter_for_group,
    users_filter_for_user,
)
from octowatch_mcp.period import DATE_FMT, parse_datetime, resolve_period

__all__ = [
    "ACCOUNT_READONLY_SOURCES",
    "ANALYTICS_VIEWS",
    "DASHBOARD_WIDGETS",
    "DATE_FMT",
    "DIRECTORY_SOURCES",
    "MONITORING_KINDS",
    "STREAM_META_SOURCES",
    "USER_INFO_SOURCES",
    "OctoWatchAPIError",
    "OctoWatchClient",
    "build_users_filter",
    "parse_datetime",
    "resolve_period",
    "users_filter_all",
    "users_filter_for_group",
    "users_filter_for_user",
]

MONITORING_KINDS = frozenset(
    {
        "Sites",
        "Apps",
        "Installs",
        "Screens",
        "Keystrokes",
        "Clipboard1",
        "SearchQueries",
        "WebForms",
        "Messengers",
        "Mail",
        "WebcamAudio",
        "Files",
        "Crawler",
        "USBExplorer",
        "Prints",
        "NetworkInterfaces",
        "WiFis",
        "Traffic",
        "TrafficSum",
    }
)

DASHBOARD_WIDGETS: dict[str, str] = {
    "users": "/api/Dashboard/GetUsers",
    "screens": "/api/Dashboard/GetScreens",
    "risks": "/api/Dashboard/GetRisks",
    "alerts": "/api/Dashboard/GetAlerts",
    "top10_risks_alerts": "/api/Dashboard/GetTop10RisksAlerts",
    "productivity_by_day": "/api/Dashboard/GetProductivityByDay",
    "applications": "/api/Dashboard/GetApplications",
    "websites": "/api/Dashboard/GetWebsites",
    "top10_users": "/api/Dashboard/GetTop10Users",
    "top10_groups": "/api/Dashboard/GetTop10Groups",
    "metric1": "/api/Productivity/GetDashboardMetric1",
}

ANALYTICS_VIEWS: dict[str, str] = {
    "overall": "/api/Analytics/Overall",
    "disciplina": "/api/Analytics/GetDisciplina",
    "activity": "/api/Analytics/GetActivity",
    "productivity": "/api/Analytics/GetProductivity",
}

DIRECTORY_SOURCES: dict[str, str] = {
    "users_groups": "/api/Edit/GetUsersGroups2",
    "users": "/api/Edit/GetUsers",
    "groups": "/api/Edit/GetGroups",
    "list_groups": "/api/Edit/GetListGroups",
    "computers": "/api/Edit/GetComputers2",
    "additional_users": "/api/Edit/GetAdditionalUsers",
    "additional_rights": "/api/Edit/GetAdditionalUsersRights",
}

USER_INFO_SOURCES: dict[str, tuple[str, str]] = {
    # source -> (method, path) — headers differ; see get_user_info()
    "user_data": ("GET", "/api/Edit/GetUserData2"),
    "tooltip": ("GET", "/api/Edit/GetUserDetailsForToolTip"),
    "group": ("GET", "/api/Edit/GetGroup"),  # group path for AliasID (user)
    "computer": ("GET", "/api/Edit/GetComputer"),  # needs ComputerGuid
    "users_from_computer": ("GET", "/api/Edit/GetUsersFromComputer"),  # needs ComputerGuid
}

ACCOUNT_READONLY_SOURCES: dict[str, str] = {
    "profiles": "/api/Account/GetProfiles2",
    "computer_profiles": "/api/Account/GetComputerProfiles",
    "timetable": "/api/Account/GetProfileTimeTable",
    "rules": "/api/Account/GetProfileRules2",
    "profile_settings": "/api/Account/GetProfileSettings",
    "computer_settings": "/api/Account/GetProfileComputerSettings",
    "account_settings": "/api/Account/GetAccountSettings",
    "categories": "/api/Edit/GetCategories",
    "top_websites": "/api/Edit/Get50Websites",
    "top_apps": "/api/Edit/Get50Apps",
    "price_settings": "/api/Tree/GetPriceSettings",
    "num_users": "/api/Account/GetNumUsers",
    "license": "/api/Account/getlicenseinfo-jwt",
    "license_expired": "/api/Account/getlicenseinfo-expired-jwt",
    "license_support": "/api/Account/getlicenseinfo-support-jwt",
    "reports": "/api/Account/GetReports",
    "processing_tasks": "/api/Edit/GetProcessingTasks",
}

STREAM_META_SOURCES: dict[str, str] = {
    "which_content": "/api/Stream/WhichContentExists",
    "videos": "/api/Stream/GetVideos",
    "downloads": "/api/Stream/GetDownloads",
}


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
        self._users_groups_cache: Any = None
        self._users_groups_cached_at: float = 0.0
        # Guards token/cache mutations during search_monitoring ThreadPoolExecutor.
        self._lock = threading.RLock()
        self._http = httpx.Client(
            base_url=self.settings.api_base,
            timeout=60.0,
            headers={"Accept": "application/json"},
        )

    # Session cache TTL for GetUsersGroups2 (seconds). 0 = until login/invalidate.
    USERS_GROUPS_CACHE_TTL = 300.0

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # --- auth -----------------------------------------------------------------

    def login(self) -> dict[str, Any]:
        with self._lock:
            email = quote(self.settings.email, safe="")
            password = quote(self.settings.password, safe="")
            path = f"/api/Access/login-jwt?email={email}&password={password}"
            data = self._request_json("GET", path, auth=False)
            if not isinstance(data, dict) or not data.get("Token"):
                raise OctoWatchAPIError(
                    f"login-jwt failed: {(data or {}).get('Message') if isinstance(data, dict) else data}",
                    body=str(data),
                )
            self._token = data["Token"]
            self._refresh_token = data.get("RefreshToken")
            self._public_id = str(data.get("PublicID") or "")
            expires_in = int(data.get("ExpiresIn") or 3600)
            self._expires_at = time.time() + max(60, expires_in - 60)
            self.invalidate_users_groups_cache()
            return data

    def ensure_auth(self) -> None:
        with self._lock:
            if self._token and time.time() < self._expires_at:
                return
            if self._token and self._refresh_token and self._public_id:
                try:
                    self.refresh()
                    return
                except OctoWatchAPIError:
                    pass
            self.login()

    def refresh(self) -> dict[str, Any]:
        with self._lock:
            if not self._refresh_token or not self._public_id:
                raise OctoWatchAPIError("No refresh token; call login() first")
            rt = quote(self._refresh_token, safe="")
            pid = quote(self._public_id, safe="")
            path = f"/api/Access/refresh-token?refresh_Token={rt}&PublicID={pid}"
            data = self._request_json("GET", path, auth=False)
            if not isinstance(data, dict) or not data.get("Token"):
                raise OctoWatchAPIError(
                    f"refresh-token failed: {data}",
                    body=str(data),
                )
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
            with self._lock:
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
            with self._lock:
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
        offset: int = 0,
        num_rows: int = 500,
        **kwargs: Any,
    ) -> Any:
        df, dt = resolve_period(date_from, date_to, self.settings.default_days)
        headers = {
            "Content-Type": "application/json",
            "DateFrom": df.strftime(DATE_FMT),
            "DateTo": dt.strftime(DATE_FMT),
            "Offset": str(max(0, offset)),
            "NumRows": str(max(1, min(num_rows, 500))),
            "HideHidden": "False",
        }
        if extra_headers:
            headers.update(extra_headers)
        body = users_filter if users_filter is not None else users_filter_all()
        return self._request_json("POST", path, headers=headers, json_body=body, **kwargs)

    def period_filter(
        self,
        *,
        group_id: int | None = None,
        user_id: int | None = None,
        users_filter: list[dict[str, int]] | None = None,
    ) -> list[dict[str, int]]:
        if users_filter is not None:
            return users_filter
        return build_users_filter(group_id=group_id, user_id=user_id)

    # --- directory / reports --------------------------------------------------

    def get_users_groups(self, *, force_refresh: bool = False) -> Any:
        """GET Edit/GetUsersGroups2 with per-client session cache.

        Agents call the tree often; cache avoids repeat round-trips.
        Invalidated on login and after USERS_GROUPS_CACHE_TTL (default 5 min).
        """
        with self._lock:
            now = time.time()
            ttl = self.USERS_GROUPS_CACHE_TTL
            fresh = (
                self._users_groups_cache is not None
                and (ttl <= 0 or (now - self._users_groups_cached_at) < ttl)
            )
            if not force_refresh and fresh:
                return self._users_groups_cache
        # Fetch outside lock to avoid holding lock during HTTP.
        data = self.get("/api/Edit/GetUsersGroups2")
        with self._lock:
            self._users_groups_cache = data
            self._users_groups_cached_at = time.time()
            return self._users_groups_cache

    def invalidate_users_groups_cache(self) -> None:
        self._users_groups_cache = None
        self._users_groups_cached_at = 0.0

    def get_users(self) -> Any:
        return self.get("/api/Edit/GetUsers")

    def get_groups(self) -> Any:
        return self.get("/api/Edit/GetGroups")

    def get_reports_settings(self) -> Any:
        return self.get("/api/Account/GetReports")

    def get_processing_tasks(self) -> Any:
        return self.get("/api/Edit/GetProcessingTasks")

    def get_directory(self, source: str, *, force_refresh: bool = False) -> Any:
        path = DIRECTORY_SOURCES.get(source)
        if not path:
            raise OctoWatchAPIError(
                f"Unknown directory source={source!r}; "
                f"choose from {sorted(DIRECTORY_SOURCES)}"
            )
        if source == "users_groups":
            return self.get_users_groups(force_refresh=force_refresh)
        return self.get(path)

    def get_account_readonly(
        self,
        source: str,
        *,
        profiles_type: int | None = None,
        alias_id: int | None = None,
        alias_type: int | None = None,
        profile_id: int | None = None,
        computer_guid: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        """Account/Edit Get* aligned with web console headers."""
        path = ACCOUNT_READONLY_SOURCES.get(source)
        if not path:
            raise OctoWatchAPIError(
                f"Unknown account source={source!r}; "
                f"choose from {sorted(ACCOUNT_READONLY_SOURCES)}"
            )
        hdrs = dict(extra_headers or {})

        if source == "profiles":
            # SPA: ProfilesType + AliasID + AliasType (defaults -1, -1)
            hdrs["ProfilesType"] = str(0 if profiles_type is None else profiles_type)
            hdrs["AliasID"] = str(-1 if alias_id is None else alias_id)
            hdrs["AliasType"] = str(-1 if alias_type is None else alias_type)
        elif source == "computer_profiles":
            if computer_guid:
                hdrs["Guid"] = computer_guid
        elif source == "timetable":
            # GetProfileTimeTable needs ProfileTimeTableID
            if profile_id is None:
                raise OctoWatchAPIError(
                    "source=timetable requires profile_id (ProfileTimeTableID)"
                )
            hdrs["ProfileTimeTableID"] = str(profile_id)
        elif source == "rules":
            if profile_id is None:
                raise OctoWatchAPIError("source=rules requires profile_id (ProfileRulesID)")
            hdrs["ProfileRulesID"] = str(profile_id)
        elif source == "profile_settings":
            if profile_id is None:
                raise OctoWatchAPIError(
                    "source=profile_settings requires profile_id (ProfileSettingsID)"
                )
            hdrs["ProfileSettingsID"] = str(profile_id)
        elif source == "computer_settings":
            if profile_id is None:
                raise OctoWatchAPIError(
                    "source=computer_settings requires profile_id "
                    "(ProfileComputerSettingsID)"
                )
            hdrs["ProfileComputerSettingsID"] = str(profile_id)

        if source.startswith("license"):
            email = quote(self.settings.email, safe="")
            password = quote(self.settings.password, safe="")
            sep = "&" if "?" in path else "?"
            path = f"{path}{sep}email={email}&password={password}"

        if hdrs:
            return self.get(path, headers=hdrs)
        return self.get(path)

    def get_user_info(
        self,
        source: str,
        *,
        alias_id: int | None = None,
        computer_guid: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> Any:
        """User/computer detail Gets — same headers as my-analytics SPA."""
        if source not in USER_INFO_SOURCES:
            raise OctoWatchAPIError(
                f"Unknown user_info source={source!r}; "
                f"choose from {sorted(USER_INFO_SOURCES)}"
            )
        method, path = USER_INFO_SOURCES[source]
        hdrs: dict[str, str] = {}

        if source == "user_data":
            # SPA: GET DateFrom, DateTo, AliasID (not POST TreeviewUsers)
            if alias_id is None:
                raise OctoWatchAPIError("source=user_data requires alias_id (AliasID)")
            df, dt = resolve_period(date_from, date_to, self.settings.default_days)
            hdrs = {
                "DateFrom": df.strftime(DATE_FMT),
                "DateTo": dt.strftime(DATE_FMT),
                "AliasID": str(alias_id),
            }
            return self._request_json(method, path, headers=hdrs)

        if source in ("tooltip", "group"):
            # GetGroup = group path for a user (AliasID), not "load group by GroupID"
            if alias_id is None:
                raise OctoWatchAPIError(f"source={source} requires alias_id (AliasID)")
            hdrs["AliasID"] = str(alias_id)
            return self._request_json(method, path, headers=hdrs)

        if source in ("computer", "users_from_computer"):
            if not computer_guid:
                raise OctoWatchAPIError(
                    f"source={source} requires computer_guid (ComputerGuid header)"
                )
            # SPA uses encodeURIComponent on the header value
            hdrs["ComputerGuid"] = quote(computer_guid, safe="")
            return self._request_json(method, path, headers=hdrs)

        return self._request_json(method, path, headers=hdrs or None)

    # --- core Overall APIs ----------------------------------------------------

    def risks(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
        offset: int = 0,
        num_rows: int = 100,
        filter_key: str | None = None,
    ) -> Any:
        extra: dict[str, str] = {}
        if filter_key:
            extra["FilterKey"] = quote(filter_key, safe="")
        return self.post(
            "/api/Risks/Overall2",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
            offset=offset,
            num_rows=num_rows,
            extra_headers=extra or None,
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
        extra: dict[str, str] = {}
        if filter_key:
            extra["FilterKey"] = quote(filter_key, safe="")
        return self.post(
            "/api/Alerts/Overall2",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
            offset=offset,
            num_rows=num_rows,
            extra_headers=extra or None,
        )

    def activity(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
        filter_key: str | None = None,
    ) -> Any:
        extra: dict[str, str] = {}
        if filter_key:
            extra["FilterKey"] = quote(filter_key, safe="")
        return self.post(
            "/api/Activity/Overall2",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
            extra_headers=extra or None,
        )

    def activity_window(
        self,
        *,
        activity_name: str,
        is_website: bool = False,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
    ) -> Any:
        return self.post(
            "/api/Activity/ActivityWindow",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
            extra_headers={
                "ActivityName": activity_name,
                "IsWebsite": "True" if is_website else "False",
            },
        )

    def category_window(
        self,
        *,
        guid: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
    ) -> Any:
        return self.post(
            "/api/Activity/CategoryWindow",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
            extra_headers={"Guid": guid},
        )

    def timesheet(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
        offset: int = 0,
        num_rows: int = 500,
    ) -> Any:
        return self.post(
            "/api/TimeSheet/Overall2",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
            offset=offset,
            num_rows=num_rows,
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

    def day_structure_list(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
    ) -> Any:
        return self.post(
            "/api/Productivity/DayStructureList",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
        )

    def day_structure(
        self,
        *,
        user_id: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        productivity_filter: int = 0,
        activity_type_filter: int = 0,
    ) -> Any:
        """GET Productivity/GetDayStructure — SPA always sends both filter headers."""
        df, dt = resolve_period(date_from, date_to, self.settings.default_days)
        headers = {
            "DateFrom": df.strftime(DATE_FMT),
            "DateTo": dt.strftime(DATE_FMT),
            "UserID": str(user_id),
            "ProductivityFilter": str(int(productivity_filter)),
            "ActivityTypeFilter": str(int(activity_type_filter)),
        }
        return self._request_json("GET", "/api/Productivity/GetDayStructure", headers=headers)

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

    def analytics_view(
        self,
        view: str,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
    ) -> Any:
        path = ANALYTICS_VIEWS.get(view)
        if not path:
            raise OctoWatchAPIError(
                f"Unknown analytics view={view!r}; choose from {sorted(ANALYTICS_VIEWS)}"
            )
        return self.post(
            path,
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
        )

    def chrono(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
        offset: int = 0,
        num_rows: int = 100,
        filter_key: str | None = None,
    ) -> Any:
        extra: dict[str, str] = {}
        if filter_key:
            extra["FilterKey"] = quote(filter_key, safe="")
        return self.post(
            "/api/Chrono/Overall2",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
            offset=offset,
            num_rows=num_rows,
            extra_headers=extra or None,
        )

    def dashboard_widget(
        self,
        widget: str,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
        num_screens: int = 6,
        videos: bool = False,
        screens: bool = True,
        by_day: bool = True,
    ) -> Any:
        path = DASHBOARD_WIDGETS.get(widget)
        if not path:
            raise OctoWatchAPIError(
                f"Unknown dashboard widget={widget!r}; "
                f"choose from {sorted(DASHBOARD_WIDGETS)}"
            )
        extra: dict[str, str] = {}
        if widget == "screens":
            extra["NumScreens"] = str(max(1, min(num_screens, 24)))
            extra["Videos"] = "1" if videos else "0"
            extra["Screens"] = "1" if screens else "0"
        if widget == "productivity_by_day":
            extra["ByDay"] = "True" if by_day else "False"
        return self.post(
            path,
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
            extra_headers=extra or None,
        )

    def monitoring(
        self,
        kind: str,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
        offset: int = 0,
        num_rows: int = 100,
        filter_key: str | None = None,
        filter_objects: str | None = None,
        videos: bool = False,
        screens: bool = True,
        screen_type: str | None = None,
    ) -> Any:
        if kind not in MONITORING_KINDS:
            raise OctoWatchAPIError(
                f"Unknown monitoring kind={kind!r}; choose from {sorted(MONITORING_KINDS)}"
            )
        extra: dict[str, str] = {}
        if filter_key:
            extra["FilterKey"] = quote(filter_key, safe="")
        if filter_objects:
            extra["FilterObjects"] = quote(filter_objects, safe="")
        if kind == "Screens":
            extra["Videos"] = "1" if videos else "0"
            extra["Screens"] = "1" if screens else "0"
            if screen_type is not None:
                extra["ScreenType"] = screen_type
        return self.post(
            f"/api/Monitoring/{kind}",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
            offset=offset,
            num_rows=num_rows,
            extra_headers=extra or None,
        )

    def tools_search(
        self,
        *,
        filter_key: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
        offset: int = 0,
        per_source_limit: int = 20,
        max_rows: int = 50,
        kinds: list[str] | None = None,
    ) -> dict[str, Any]:
        """Console Tools → Search fan-out across Monitoring kinds."""
        from octowatch_mcp.tools_search import execute_tools_search

        return execute_tools_search(
            self.monitoring,
            filter_key=filter_key,
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
            offset=offset,
            per_source_limit=per_source_limit,
            max_rows=max_rows,
            kinds=kinds,
        )

    def live_overall(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        users_filter: list[dict[str, int]] | None = None,
    ) -> Any:
        return self.post(
            "/api/Live/Overall2",
            date_from=date_from,
            date_to=date_to,
            users_filter=users_filter,
        )

    def stream_meta(
        self,
        source: str,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        alias_id: int | None = None,
        at: datetime | None = None,
    ) -> Any:
        """Stream meta — SPA uses GET (not period POST + TreeviewUsers).

        which_content: GET AliasID + DateTime → raw int 0|1|2 (not JSON object)
        videos: GET DateFrom + DateTo + UserID
        downloads: GET (Bearer only)
        """
        if source not in STREAM_META_SOURCES:
            raise OctoWatchAPIError(
                f"Unknown stream source={source!r}; "
                f"choose from {sorted(STREAM_META_SOURCES)}"
            )
        path = STREAM_META_SOURCES[source]

        if source == "downloads":
            return self.get(path)

        if source == "which_content":
            if alias_id is None:
                raise OctoWatchAPIError("which_content requires alias_id (AliasID)")
            # Prefer explicit at, then period end (DateTo), then DateFrom.
            when = at or date_to or date_from
            if when is None:
                when = resolve_period(None, None, self.settings.default_days)[1]
            # Response is a bare integer (or quoted), not a JSON object.
            with self._lock:
                self.ensure_auth()
                token = self._token
            hdrs = {
                "Authorization": f"Bearer {token}",
                "AliasID": str(alias_id),
                "DateTime": when.strftime(DATE_FMT),
            }
            response = self._http.request("GET", path, headers=hdrs)
            if response.status_code == 401:
                with self._lock:
                    self.login()
                    token = self._token
                hdrs["Authorization"] = f"Bearer {token}"
                response = self._http.request("GET", path, headers=hdrs)
            if response.status_code >= 400:
                raise OctoWatchAPIError(
                    f"GET {path} → HTTP {response.status_code}: {response.text[:500]}",
                    status_code=response.status_code,
                    body=response.text,
                )
            text = (response.text or "").strip().strip('"')
            if not text:
                value = 0
            else:
                try:
                    value = int(text)
                except ValueError as exc:
                    raise OctoWatchAPIError(
                        f"GET {path}: expected int 0|1|2, got {text[:80]!r}",
                        status_code=response.status_code,
                        body=response.text[:200],
                    ) from exc
            if value not in (0, 1, 2):
                raise OctoWatchAPIError(
                    f"GET {path}: WhichContentExists out of range: {value}",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
            return {
                "WhichContentExists": value,
                "meaning": {
                    0: "both_or_none_or_error",
                    1: "screenshots_only",
                    2: "video_only",
                }[value],
            }

        # videos
        if alias_id is None:
            raise OctoWatchAPIError("videos requires alias_id / user_id (UserID header)")
        df, dt = resolve_period(date_from, date_to, self.settings.default_days)
        return self.get(
            path,
            headers={
                "DateFrom": df.strftime(DATE_FMT),
                "DateTo": dt.strftime(DATE_FMT),
                "UserID": str(alias_id),
            },
        )
