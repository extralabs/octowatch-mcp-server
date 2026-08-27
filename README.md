# octowatch-mcp

Read-only [MCP](https://modelcontextprotocol.io/) server for **OctoWatch DLP Cloud**.

Ask Claude / Cursor / ChatGPT in plain language:

- “Which **Risks** in the last day?”
- “Who was idle the longest yesterday?”
- “Productivity summary for Accounting”
- “Show users and groups”

Python MCP SDK **v2** (`MCPServer`). Built for SecOps and managers — and as open-source PR for [octowatchdlp.com](https://octowatchdlp.com).

> **Security:** defaults use the public **demo** account.  
> **Do not put production passwords in MCP config or git.** Use env vars and a least-privilege console operator.

## Status

Alpha (`v0.2.0`): live Cloud API + agent-friendly summaries (dates, Risks rollup, idle, compact productivity/activity/timesheet).

| Tool | API | Notes |
|------|-----|--------|
| `octowatch_whoami` | `Access/login-jwt` | Account / host (no password) |
| `list_users_groups` | `Edit/GetUsersGroups2` | Tree: Type 0 root, 1 group, 2 user |
| `list_risks` | `Analytics/Overall` + `Risks/Overall2` | Default `mode=summary`; `raw` / `fetch_all` available |
| `list_anomalies` | `Alerts/Overall2` | Formal deviations only (not idle duration) |
| `get_idle_summary` | `Productivity/Overall3` | Rank by `InactiveTime` |
| `get_activity_summary` | `Activity/Overall2` | Top apps/sites (compact default) |
| `get_timesheet` | `TimeSheet/Overall2` | Per-day worked vs expected hours |
| `get_productivity_summary` | `Overall3` + stats + analytics | Per-user rollup |
| `list_reports` | `GetReports` + `GetProcessingTasks` | ReportTypes labeled when known |

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

### Periods

Prefer `period=today|yesterday|last_7_days|last_30_days`, or `date_from` / `date_to`.

- Date-only values cover the **full calendar day** (`date_to` → `23:59:59`).
- Optional `user_id` (AliasID) and `group_id` on most read tools.

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
Internal notes: [docs/API.md](docs/API.md).

## Roadmap

- [x] Date-only full-day fix + relative `period`
- [x] Risks summary + idle helper + compact formatters
- [x] Client-side `user_id` (AliasID) filter
- [ ] Report generator queue (`Edit/QueueReportEmail`) as optional write-opt-in
- [ ] PyPI publish + GitHub Action smoke against demo
- [ ] TypeScript port (optional)

## License

MIT — see [LICENSE](LICENSE).
