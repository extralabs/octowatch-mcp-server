# API notes (MCP coverage audit)

Prefer the interactive UI at https://app.octowatchdlp.com/api/ for the full catalog.  
Help catalog: https://cloud.octowatchdlp.com/Help (~340 endpoints).

This document is the **public gap matrix** for `octowatch-mcp` vs the Cloud **web console** (read-only).

## Hosts

| URL | Role |
|-----|------|
| `https://app.octowatchdlp.com` | Web Console SPA |
| `https://app.octowatchdlp.com/api/` | In-app API docs (SPA route) |
| `https://cloud.octowatchdlp.com` | REST API (`spm-config.json` → `serverBase`) |
| `https://cloud.octowatchdlp.com/Help` | ASP.NET Web API Help |

## Auth

```http
GET /api/Access/login-jwt?email=demo%40octowatchdlp.com&password=demo
```

Response includes `Token`, `RefreshToken`, `ExpiresIn`, `PublicID`.

```http
GET /api/Access/refresh-token?refresh_Token=…&PublicID=…
Authorization: Bearer <Token>   # on data calls
```

## Users / groups filter body (`TreeviewUsers`)

Period POSTs send a JSON array. The server uses **`NodeType` + `UserID` only**.

```json
[{ "NodeType": -666666, "UserID": -666666 }]
```

| NodeType | Meaning | UserID |
|----------|---------|--------|
| `-666666` | All users (root) | `-666666` |
| `14` | Group | group id |
| `1` | User | AliasID |

**Do not confuse** with `GET /api/Edit/GetUsersGroups2` item fields:

| GetUsersGroups2 `Type` | Meaning |
|------------------------|---------|
| `0` | Root / all |
| `1` | Group |
| `2` | User |

Those UI `Type` values are **not** POST `NodeType` values. MCP maps `group_id` → NodeType **14**, `user_id` → NodeType **1**. Both may be sent together (server ORs them).

Wire JSON is **PascalCase** (`List`, `AliasID`, `InactiveTime`, `TotalRecords`). Overall2 wrappers typically expose `List` + paging fields (`TotalRecords`, `StartFrom`, `NumRecords`).

## Headers for period POSTs

```
Authorization: Bearer <Token>
Accept: application/json
Content-Type: application/json
DateFrom: 2026-08-20 00:00:00
DateTo: 2026-08-27 23:59:59
Offset: 0
NumRows: 100
HideHidden: False
```

Optional: `FilterKey`, `FilterObjects` (URL-encoded). Screens also use `Videos` / `Screens` / `ScreenType`.

**MCP date rule:** date-only `YYYY-MM-DD` for `date_to` is sent as end of day `23:59:59`.

## Coverage matrix (console vs MCP)

Status values:

| Status | Meaning |
|--------|---------|
| `covered` | Available via MCP tool (full or structured) |
| `covered_compact` | Available; default response truncated / blobs stripped |
| `out_of_scope_write` | Console mutate — not in read-only MCP |
| `out_of_scope_binary` | Binary/media download or live frames |
| `out_of_scope_not_in_console` | On Help/backend but not used by current SPA |
| `intentional_skip` | Read-only but unsafe for agents (e.g. PIN) |

| Console area | Endpoint | MCP tool | Status |
|--------------|----------|----------|--------|
| Auth | `GET /api/Access/login-jwt` | `octowatch_whoami` | covered |
| Auth | `GET /api/Access/refresh-token` | (client) | covered |
| Directory | `GET /api/Edit/GetUsersGroups2` | `list_users_groups` / `list_directory` | covered |
| Directory | `GetUsers` / `GetGroups` / `GetListGroups` / `GetComputers2` | `list_directory` | covered |
| Directory | `GetAdditionalUsers` / `GetAdditionalUsersRights` | `list_directory` | covered |
| Directory | New/Rename/Move/Remove/Merge users & groups | — | out_of_scope_write |
| Risks | `POST /api/Risks/Overall2` | `list_risks` | covered_compact |
| Alerts | `POST /api/Alerts/Overall2` | `list_anomalies` | covered_compact |
| Risks/Alerts | ShowHide / SetMarker2 / RemoveRecord2 / AddAIBlackList | — | out_of_scope_write |
| Activity | `POST /api/Activity/Overall2` | `get_activity_summary` | covered_compact |
| Activity | `ActivityWindow` / `CategoryWindow` | `get_activity_detail` | covered_compact |
| Chrono | `POST /api/Chrono/Overall2` | `get_chrono` | covered_compact |
| TimeSheet | `POST /api/TimeSheet/Overall2` | `get_timesheet` | covered_compact |
| TimeSheet | SetComment / RemoveComment | — | out_of_scope_write |
| Productivity | `Overall3` / `GetStats` | `get_productivity_summary` / `get_idle_summary` | covered_compact |
| Productivity | `DayStructureList` / `GetDayStructure` | `get_day_structure` | covered |
| Productivity | `GetDashboardMetric1` | `get_dashboard` widget=`metric1` | covered |
| Analytics | `Overall` / `GetDisciplina` / `GetActivity` / `GetProductivity` | `get_analytics` | covered |
| Dashboard | `Dashboard/Get*` widgets | `get_dashboard` | covered_compact |
| Monitoring | `POST /api/Monitoring/{Sites,Apps,…}` | `list_monitoring` | covered_compact |
| Monitoring | Tools → Search fan-out (`FilterKey` + per-kind `FilterObjects`) | `search_monitoring` | covered_compact |
| Monitoring media | Screenshots / Clipboard / Files / Prints / Webcam Get* binaries | — | out_of_scope_binary |
| Online | `POST /api/Live/Overall2` | `list_online` | covered |
| Online | Live webcam / LiveStream / VNC / RemoteControl | — | out_of_scope_binary |
| Stream | `WhichContentExists` / `GetVideos` / `GetDownloads` | `list_stream_meta` | covered |
| Stream | `GetVideoWithSeek` / `DownloadVideo` / `ExportVideo` | — | out_of_scope_binary |
| Users | `GetUserData2` / tooltip / `GetGroup` / `GetComputer` / `GetUsersFromComputer` | `get_user_info` | covered |
| Account | Profiles / timetable / rules / settings / categories / Get50* / price / license / num users | `get_account_readonly` | covered |
| Account | `GetUninstallPin1` | — | intentional_skip |
| Account | Set* / RecalcProductivity / PostCategories / … | — | out_of_scope_write |
| Reports | `GetReports` + `GetProcessingTasks` | `list_reports` / `get_account_readonly` | covered |
| Reports | `QueueReportEmail` / `SetReports` | — | out_of_scope_write |
| Other | CustomReports / Geo / Archive / legacy XML Overall | — | out_of_scope_not_in_console |
| Billing | `Pay/*` | — | out_of_scope_write |
| Meta | (this matrix) | `list_api_coverage` | covered |

### Risks summary behavior

- `by_user`: from `Analytics/Overall` (accurate totals without paging all risk rows).
- `by_rule` / `by_day` / `sample`: from one `Risks/Overall2` page unless `fetch_all=true` (cap 2000).

### Idle vs anomalies

- **Idle duration** → productivity `InactiveTime` (`get_idle_summary`).
- **Formal deviations** → `Alerts/Overall2` (`list_anomalies`). Empty Alerts with a 24h timetable is expected.

### Payload guards

MCP defaults: `limit` ≤ 100 (hard cap 500), `compact=true` strips blob-like fields and truncates long text (keystrokes, mail bodies, OCR).

## SPA header contracts (aligned)

These differ from the usual period POST + TreeviewUsers pattern:

| Endpoint | Method | Required headers |
|----------|--------|------------------|
| `Edit/GetUserData2` | GET | `DateFrom`, `DateTo`, `AliasID` |
| `Edit/GetUserDetailsForToolTip` | GET | `AliasID` |
| `Edit/GetGroup` | GET | `AliasID` (group *path* for that user) |
| `Edit/GetComputer` / `GetUsersFromComputer` | GET | `ComputerGuid` |
| `Productivity/GetDayStructure` | GET | `UserID`, `DateFrom`, `DateTo`, `ProductivityFilter`, `ActivityTypeFilter` |
| `Account/GetProfiles2` | GET | `ProfilesType`, `AliasID`, `AliasType` (defaults `-1`) |
| `Account/GetProfileTimeTable` | GET | `ProfileTimeTableID` |
| `Account/GetProfileRules2` | GET | `ProfileRulesID` |
| `Account/GetProfileSettings` | GET | `ProfileSettingsID` |
| `Account/GetProfileComputerSettings` | GET | `ProfileComputerSettingsID` |
| `Account/GetComputerProfiles` | GET | optional `Guid` |
| `Stream/WhichContentExists` | GET | `AliasID`, `DateTime` (raw int body) |
| `Stream/GetVideos` | GET | `DateFrom`, `DateTo`, `UserID` |
| `Stream/GetDownloads` | GET | Bearer only |

### Tools → Search (`search_monitoring`)

Same fan-out as the console: parallel Monitoring POSTs with `FilterKey` and default `FilterObjects`:

| Kind | FilterObjects |
|------|---------------|
| Sites | `url,wt` |
| Apps | `app,wt` |
| Keystrokes | `app,keystrokestext` |
| Clipboard1 | `app,clipboardtext` |
| Screens | `ocr,url,wt` (Videos=0) |
| Messengers | `chatstext` |
| Mail | `chatstext,sender,recipient,subject` |
| WebcamAudio | `ar,wt` |
| Files | `files_file` |
| Prints | `prints_file` |
| Installs | _(none)_ |
| NetworkInterfaces | _(none)_ |
| WebForms | `url` |

Not included (same as SPA): SearchQueries, Risks, Crawler, USBExplorer, Traffic*.

## Demo tree (sample)

Groups: Managers, Accounting, Management, Production, Warehouse.  
Users include Accountant Emily Carter (`AliasID` 4), Madison Harris (1), Cooper Sullivan (2), Tyler Benson (3), Jackson T.R. (5), Hudson Blake (6).
