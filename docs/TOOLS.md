# Tools reference

MCP tool arguments and **when to use which tool**. Runtime routing text is also exposed as resource `octowatch://tool-routing` (keep this doc aligned when changing `server.py` instructions).

Product UI and REST details stay at [octowatchdlp.com/docs/](https://octowatchdlp.com/docs/) and [app.octowatchdlp.com/api/](https://app.octowatchdlp.com/api/). Below is MCP-only guidance.

## Common arguments

Most period tools accept:

| Arg | Description |
|-----|-------------|
| `period` | `today` \| `yesterday` \| `last_7_days` \| `last_30_days` (wins over dates when set) |
| `date_from` / `date_to` | `YYYY-MM-DD` or `YYYY-MM-DD HH:MM:SS`; date-only `date_to` → end of day `23:59:59` |
| `group_id` | Console group id → TreeviewUsers **NodeType=14** |
| `user_id` | User **AliasID** → TreeviewUsers **NodeType=1** |
| `limit` | Max rows (default 100, hard cap 500) |
| `offset` | Pagination offset |
| `compact` | Default `true` — strip blob-like fields / truncate long text |

Do **not** confuse directory tree `Type` (0/1/2 from `GetUsersGroups2`) with POST `NodeType` (14 group / 1 user).

## When which tool

| You want… | Use | Not |
|-----------|-----|-----|
| Idle / inactive time | `get_idle_summary` | `list_anomalies` |
| Formal lateness / overtime / timetable alerts | `list_anomalies` | `get_idle_summary` |
| DLP / keyword / USB / policy hits | `list_risks` (`mode=summary`) | `list_anomalies` for policy |
| Top apps/sites by time | `get_activity_summary` | — |
| Drill into one app/site | `get_activity_detail` | — |
| Productivity % | `get_productivity_summary` | — |
| Attendance vs timetable | `get_timesheet` | — |
| Chronometry timeline | `get_chrono` | — |
| Day segments structure | `get_day_structure` | — |
| Keyword across monitoring | `search_monitoring(filter_key=…)` | Looping `list_monitoring` |
| One monitoring table | `list_monitoring(kind=…)` | — |
| Dashboard tile | `get_dashboard(widget=…)` | — |
| Analytics chart | `get_analytics(view=…)` | — |
| Online presence | `list_online` | Live video frames |
| Video metadata | `list_stream_meta` | Binary download |
| Users/groups tree | `list_users_groups` / `list_directory` | — |
| Person card | `get_user_info` | — |
| Profiles / license Gets | `get_account_readonly` | Set\* / PIN |
| Reports queue | `list_reports` | — |
| Coverage gaps | `list_api_coverage` | — |
| Account / host | `octowatch_whoami` | — |

Empty formal alerts on a 24h timetable are normal. Prefer relative `period` over raw dates when possible.

## Scenario cases

| Goal | Suggested flow | Example ask |
|------|----------------|-------------|
| Daily risks brief | `list_risks(period=today, mode=summary)` → map ids via `list_users_groups` | “Summarize today’s risks by user and rule” |
| Idle review | `get_idle_summary(period=yesterday)` optional `min_idle_hours` | “Who was idle longest yesterday?” |
| Group productivity | `get_productivity_summary` + `group_id` | “Productivity for Accounting last 7 days” |
| Keyword hunt | `search_monitoring(filter_key=…, period=…)` | “Find `invoice` in monitoring last week” |
| User drill-down | `get_user_info` → `get_activity_summary` → optional `get_activity_detail` | “What did user AliasID 4 do today?” |

Host prompts (`daily_risks_brief`, `idle_review`, …) encode the same sequences — see [MCP.md](MCP.md).

---

## Core tools

### `octowatch_whoami`

No args. Returns API host and account (never the password).

### `list_users_groups`

| Arg | Default | Notes |
|-----|---------|-------|
| `refresh` | `false` | Force reload (~5 min session cache) |

Tree `Type`: 0=root, 1=group, 2=user.

### `list_risks`

| Arg | Default | Notes |
|-----|---------|-------|
| `mode` | `summary` | `summary` or `raw` |
| `fetch_all` | `false` | Cap 2000 detail rows |
| period / dates / `group_id` / `user_id` / `offset` / `limit` / `compact` | | |

Summary: `by_user` from Analytics; `by_rule` / `by_day` / `sample` from Risks page unless `fetch_all`.

### `list_anomalies`

Formal Alerts only. Args: period filters, `offset`, `limit`, `filter_key`, `compact`.

### `get_idle_summary`

Ranks by `InactiveTime`. Optional `min_idle_hours`.

### `get_activity_summary`

| Arg | Default |
|-----|---------|
| `top_n` | `15` |
| `raw` | `false` |

### `get_timesheet`

Period filters + optional `raw`.

### `get_productivity_summary`

Period filters + optional `raw` (detail + stats + analytics).

### `list_reports`

No args. Scheduled report settings + processing tasks.

---

## Console tools

### `get_analytics`

| Arg | Default | Values |
|-----|---------|--------|
| `view` | `overall` | `overall` \| `disciplina` \| `activity` \| `productivity` |

### `get_dashboard`

| Arg | Default | Values |
|-----|---------|--------|
| `widget` | `users` | `users`, `screens`, `risks`, `alerts`, `top10_risks_alerts`, `productivity_by_day`, `applications`, `websites`, `top10_users`, `top10_groups`, `metric1` |
| `num_screens` | `6` | Screens tile count |

Blobs stripped when `compact=true`.

### `get_chrono`

Chronometry timeline. Period filters, `offset`, `limit`, `filter_key`, `compact`.

### `get_day_structure`

| Arg | Default | Notes |
|-----|---------|-------|
| `mode` | `list` | `list` or `detail` (`detail` requires `user_id`) |
| `productivity_filter` | `0` | 0–4 |
| `activity_type_filter` | `0` | 0–2 |

### `list_monitoring`

| Arg | Notes |
|-----|-------|
| `kind` | Required: `Sites`, `Apps`, `Installs`, `Screens`, `Keystrokes`, `Clipboard1`, `SearchQueries`, `WebForms`, `Messengers`, `Mail`, `WebcamAudio`, `Files`, `Crawler`, `USBExplorer`, `Prints`, `NetworkInterfaces`, `WiFis`, `Traffic`, `TrafficSum` |
| `filter_objects` | Optional Monitoring filter string |

Sensitive kinds truncate text when compact. No binary media.

### `search_monitoring`

| Arg | Default | Notes |
|-----|---------|-------|
| `filter_key` | *(required)* | Keyword |
| `per_source_limit` | `20` | Per kind |
| `max_rows` | `50` | Aggregated cap |
| `kinds` | all search sources | Comma-separated subset, e.g. `Sites,Apps,Mail` |

### `get_activity_detail`

| Arg | Notes |
|-----|-------|
| `mode` | `activity_window` (needs `activity_name`) or `category_window` (needs `category_guid`) |
| `is_website` | For activity window |

### `list_online`

Presence only (`Live/Overall2`). No webcam frames.

### `list_stream_meta`

| Arg | Notes |
|-----|-------|
| `source` | `which_content` \| `videos` \| `downloads` |
| `user_id` | Required for `which_content` and `videos` |

No `DownloadVideo`.

### `list_directory`

| Arg | Default | Values |
|-----|---------|--------|
| `source` | `users_groups` | `users_groups`, `users`, `groups`, `list_groups`, `computers`, `additional_users`, `additional_rights` |
| `refresh` | `false` | Cache bypass for `users_groups` |

### `get_user_info`

| Arg | Notes |
|-----|-------|
| `source` | `user_data`, `tooltip`, `group`, `computer`, `users_from_computer` |
| `user_id` | Required for user_data / tooltip / group |
| `computer_guid` | Required for computer sources |

### `get_account_readonly`

Read-only Gets (no Set\*/PIN). `source` includes `profiles`, `computer_profiles`, `timetable`, `rules`, `profile_settings`, `computer_settings`, `account_settings`, `categories`, `top_websites`, `top_apps`, `price_settings`, `num_users`, `license`, `license_expired`, `license_support`, `reports`, `processing_tasks`. Some sources need `profile_id` / `profiles_type` / `user_id` / `computer_guid` — see tool description in the host.

### `list_api_coverage`

Static gap matrix (same data as resource `octowatch://coverage`). Narrative audit: [API.md](API.md).

---

## Toolsets

Env `OCTOWATCH_TOOLSETS` (default `all`):

- `all` — every tool
- `core` — whoami, directory tree, risks, anomalies, idle, activity, timesheet, productivity, reports
- `console` — analytics/dashboard/chrono/monitoring/… (**auto-includes core**)

## Errors

Failures raise `ToolError` → hosts see `is_error=true`. Do not parse a success JSON `"error"` key (removed in 0.5.0).
