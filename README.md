# octowatch-mcp

Read-only [MCP](https://modelcontextprotocol.io/) server for **OctoWatch DLP Cloud**.

Ask Claude / Cursor / ChatGPT in plain language:

- “Which **Risks** in the last day?”
- “Who was idle the longest yesterday?”
- “Productivity summary for Accounting”
- “Show Monitoring keystrokes for Emily”
- “List users and groups”

Python MCP SDK **v2** (`MCPServer`). Built for SecOps and managers — and as open-source PR for [octowatchdlp.com](https://octowatchdlp.com).

> **Security:** defaults use the public **demo** account.  
> **Do not put production passwords in MCP config or git.** Use env vars and a least-privilege console operator.  
> No writes, no screenshot/video binary downloads.

## Status

Alpha (`v0.4.0`): read-only coverage of Cloud **console** APIs (analytics, monitoring lists, dashboard, chrono, directory, account Gets). See [docs/API.md](docs/API.md) gap matrix or tool `list_api_coverage`.

### Core tools

| Tool | API | Notes |
|------|-----|--------|
| `octowatch_whoami` | `Access/login-jwt` | Account / host (no password) |
| `list_users_groups` | `Edit/GetUsersGroups2` | Tree: Type 0 root, 1 group, 2 user |
| `list_risks` | `Analytics/Overall` + `Risks/Overall2` | Default `mode=summary` |
| `list_anomalies` | `Alerts/Overall2` | Formal deviations (not idle) |
| `get_idle_summary` | `Productivity/Overall3` | Rank by `InactiveTime` |
| `get_activity_summary` | `Activity/Overall2` | Top apps/sites |
| `get_timesheet` | `TimeSheet/Overall2` | Worked vs expected hours |
| `get_productivity_summary` | `Overall3` + stats + analytics | Per-user rollup |
| `list_reports` | `GetReports` + `GetProcessingTasks` | ReportTypes labeled |

### Console coverage tools

| Tool | API | Notes |
|------|-----|--------|
| `get_analytics` | `Analytics/*` | `view=overall\|disciplina\|activity\|productivity` |
| `get_dashboard` | `Dashboard/Get*` + metric1 | Widgets; blobs stripped |
| `get_chrono` | `Chrono/Overall2` | Timeline |
| `get_day_structure` | `DayStructureList` / `GetDayStructure` | |
| `list_monitoring` | `Monitoring/{kind}` | 19 kinds; compact by default |
| `search_monitoring` | Tools Search fan-out | `filter_key` across 13 kinds |
| `get_activity_detail` | `ActivityWindow` / `CategoryWindow` | Drill-down |
| `list_online` | `Live/Overall2` | Presence only |
| `list_stream_meta` | Stream meta Gets | No video download |
| `list_directory` | Edit Get* directory | users/groups/computers/… |
| `get_user_info` | `GetUserData2` / tooltip / … | |
| `get_account_readonly` | Account/Edit Get* | No Set*/PIN |
| `list_api_coverage` | (static matrix) | Gap summary |

## Quick start

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -e .
cp .env.example .env   # optional; demo defaults work without it
python -m octowatch_mcp
```

### Cursor

Merge `examples/cursor-mcp.json` into your MCP settings (fix `cwd` / use `python` from the venv). Restart Cursor and try: *“List OctoWatch risks for the last week.”*

### Claude Desktop

Same shape in `examples/claude-desktop.json` → Claude Desktop MCP config.

## Configuration

| Env | Default | Meaning |
|-----|---------|---------|
| `OCTOWATCH_API_BASE` | `https://cloud.octowatchdlp.com` | API host from `spm-config.json` → `serverBase` |
| `OCTOWATCH_EMAIL` | `demo@octowatchdlp.com` | Console admin / operator |
| `OCTOWATCH_PASSWORD` | `demo` | **Demo only** |
| `OCTOWATCH_DEFAULT_DAYS` | `1` | Lookback when tool omits dates/period |

### Periods & filters

Prefer `period=today|yesterday|last_7_days|last_30_days`, or `date_from` / `date_to`.

- Date-only values cover the **full calendar day** (`date_to` → `23:59:59`).
- Optional `user_id` (AliasID) and `group_id` on most read tools.
- POST body `TreeviewUsers`: all → `NodeType=-666666`; **group → `NodeType=14`**; **user → `NodeType=1`**.

## Auth & period calls (API)

1. `GET /api/Access/login-jwt?email=…&password=…` → `Token`, `RefreshToken`, `PublicID`
2. Later requests: `Authorization: Bearer <Token>`
3. Period POSTs need headers `DateFrom` / `DateTo` as `yyyy-MM-dd HH:mm:ss`
4. Body (users/groups filter):

```json
[{ "NodeType": -666666, "UserID": -666666 }]
```

Marketing / interactive docs: [app.octowatchdlp.com/api/](https://app.octowatchdlp.com/api/).  
Help catalog: `https://cloud.octowatchdlp.com/Help`.  
Product docs: [octowatchdlp.com/docs/](https://octowatchdlp.com/docs/).  
Coverage audit: [docs/API.md](docs/API.md).

## Roadmap

- [x] Date-only full-day fix + relative `period`
- [x] Risks summary + idle helper + compact formatters
- [x] Correct TreeviewUsers NodeType (group=14, user=1)
- [x] Console read-only coverage (Monitoring, Dashboard, Chrono, Account Gets)
- [ ] Report generator queue (`Edit/QueueReportEmail`) as optional write-opt-in
- [ ] PyPI publish + GitHub Action smoke against demo
- [ ] TypeScript port (optional)

## License

MIT — see [LICENSE](LICENSE).
