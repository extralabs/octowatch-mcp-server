# MCP protocol notes (octowatch-mcp)

Read-only MCP server for [OctoWatch DLP Cloud](https://octowatchdlp.com/). Product guides and the full REST catalog stay at [octowatchdlp.com/docs/](https://octowatchdlp.com/docs/) and [app.octowatchdlp.com/api/](https://app.octowatchdlp.com/api/). This page is the **protocol surface** of the MCP package.

This server speaks MCP over **stdio** (default) or optional **Streamable HTTP**.

## Tools

- All tools set `annotations.read_only_hint=True` (and `open_world_hint=True` for Cloud API).
- Failures raise `ToolError` → hosts see `is_error=True`. Do **not** parse a success JSON `"error"` key (removed in 0.5.0).
- **All tools** return JSON objects via `structured_content` (`dict[str, Any]`). Non-object API payloads are wrapped as `{"data": ...}`.
- Argument reference and when-which-tool: [TOOLS.md](TOOLS.md).

## Resources

Hosts that support resources can read:

| URI | Notes |
|-----|--------|
| `octowatch://coverage` | Static API gap matrix (same as `list_api_coverage`) |
| `octowatch://tool-routing` | When-which-tool guide (keep in sync with [TOOLS.md](TOOLS.md)) |
| `octowatch://whoami` | Live session identity (may fail with `ResourceError`) |

How to open them depends on the host (resource picker / `@` mentions). If unsure, call the equivalent tools instead.

## Prompts

User-invoked SecOps templates (arguments vary by prompt):

| Prompt | Purpose |
|--------|---------|
| `daily_risks_brief` | Risks summary sequence (`period`) |
| `idle_review` | Idle ranking via `get_idle_summary` (`period`, optional `group_id`) |
| `user_activity_drilldown` | One-user activity path (`user_id`, `period`) |
| `monitoring_keyword_hunt` | Tools Search via `search_monitoring` (`filter_key`, `period`) |

In Claude Desktop / Cursor, use the host’s **prompt** / slash-command UI when available; otherwise paste the same intent as a normal chat message.

## Toolsets

Env `OCTOWATCH_TOOLSETS` (default `all`):

- `all` — every tool
- `core` — whoami, directory tree, risks, anomalies, idle, activity, timesheet, productivity, reports
- `console` — analytics/dashboard/chrono/monitoring/… (**auto-includes core**)
- `core,console` — same as `all`

## Transports

```bash
octowatch-mcp                          # stdio
octowatch-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

Streamable HTTP defaults to **127.0.0.1**. Binding elsewhere exposes credentials on the network — avoid unless you understand the risk. See [SECURITY.md](../SECURITY.md).

## Logging

Server logs go to **stderr** (stdout is reserved for stdio MCP framing).

## Inspector (optional)

Use the [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) against `octowatch-mcp` (stdio) to list tools, try calls, and inspect resources/prompts during development.

## Related

- Install: [hosts.md](hosts.md)
- Coverage audit: [API.md](API.md)
- Console: [app.octowatchdlp.com](https://app.octowatchdlp.com/)
