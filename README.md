# octowatch-mcp

Read-only [MCP](https://modelcontextprotocol.io/) server for **OctoWatch DLP Cloud**.

Ask Claude / Cursor / ChatGPT in plain language:

- “Which **Risks** in the last day?”
- “Who has idle / anomaly alerts?”
- “Productivity summary for Accounting”
- “Show users and groups”

Python MCP SDK **v2** (`MCPServer`). Built for SecOps and managers — and as open-source PR for [octowatchdlp.com](https://octowatchdlp.com).

> **Security:** defaults use the public **demo** account.  
> **Do not put production passwords in MCP config or git.** Use env vars and a least-privilege console operator.

## Status

Alpha scaffold (`v0.1.0`): auth + core read-only tools wired to live Cloud API.

| Tool | API | Notes |
|------|-----|--------|
| `octowatch_whoami` | `Access/login-jwt` | Account / host (no password) |
| `list_users_groups` | `Edit/GetUsersGroups2` | Tree: Type 0 root, 1 group, 2 user |
| `list_risks` | `Risks/Overall2` | Rule / DLP Risks |
| `list_anomalies` | `Alerts/Overall2` | Deviations (idle, lateness, …) |
| `get_activity_summary` | `Activity/Overall2` | Apps / sites |
| `get_timesheet` | `TimeSheet/Overall2` | Timesheet |
| `get_productivity_summary` | `Productivity/Overall3` + stats + analytics | Rollup |
| `list_reports` | `Account/GetReports` + `Edit/GetProcessingTasks` | Settings + jobs |

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
| `OCTOWATCH_DEFAULT_DAYS` | `1` | Lookback when tool omits dates |

Marketing / interactive docs live at [app.octowatchdlp.com/api/](https://app.octowatchdlp.com/api/).  
ASP.NET Help catalog: `https://cloud.octowatchdlp.com/Help`.  
Product docs: [octowatchdlp.com/docs/](https://octowatchdlp.com/docs/).

### Auth & period calls (important)

1. `GET /api/Access/login-jwt?email=…&password=…` → `Token`, `RefreshToken`, `PublicID`
2. Later requests: `Authorization: Bearer <Token>`
3. Period POSTs need headers `DateFrom` / `DateTo` as `yyyy-MM-dd HH:mm:ss`
4. Body (users/groups filter):

```json
[{ "NodeType": -666666, "UserID": -666666 }]
```

That root node means “all”. Groups use `NodeType: 1` and the group id.

## Roadmap

- [ ] Per-user filter (AliasID) without client-side post-filter
- [ ] Idle-hours helper tool (“idle > 3h”)
- [ ] Report generator queue (`Edit/QueueReportEmail`) as optional write-opt-in
- [ ] PyPI publish + GitHub Action smoke against demo
- [ ] TypeScript port (optional)

## License

MIT — see [LICENSE](LICENSE).
