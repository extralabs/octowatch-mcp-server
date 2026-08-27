# Troubleshooting

MCP-focused fixes. For product/console how-to, use [octowatchdlp.com/docs/](https://octowatchdlp.com/docs/) and verify data in the [Web Console](https://app.octowatchdlp.com/). REST shapes: [app.octowatchdlp.com/api/](https://app.octowatchdlp.com/api/).

## Auth failed / whoami errors

1. Check `OCTOWATCH_EMAIL` / `OCTOWATCH_PASSWORD` (typos, wrong tenant).
2. Confirm the host actually injects `env` (open the MCP JSON you edited).
3. For `.env` + source install, ensure `cwd` is the directory that contains `.env`.
4. Confirm `OCTOWATCH_API_BASE` is the Cloud API host, not the SPA origin (`app.octowatchdlp.com`).
5. Log in manually at [app.octowatchdlp.com](https://app.octowatchdlp.com/) with the same operator.

## Server not showing in the host

- `octowatch-mcp` (or venv `python`) must be on the PATH the **host** uses.
- Restart the host after editing MCP config.
- From-source configs need a valid absolute `cwd`.
- Check host MCP logs; server logs go to **stderr** (stdout is reserved for stdio framing).

## Empty risks / monitoring / activity

- Wrong `period` or timezone expectation — try `period=last_7_days`.
- Filters: `user_id` is **AliasID**; `group_id` is group id (NodeType 14), not tree `Type`.
- Demo tenant may simply have little data for that window — compare in the console.
- `compact=true` truncates text; it should not empty entire lists.

## Empty `list_anomalies` but people look “idle”

Formal Alerts ≠ idle time. Use `get_idle_summary` for `InactiveTime`. Empty Alerts on a 24h timetable is expected. See [TOOLS.md](TOOLS.md#when-which-tool).

## Agent used the wrong tool

Share the when-which table or invoke prompt `idle_review` / `daily_risks_brief`. Resource `octowatch://tool-routing` carries the same guidance.

## Large / truncated payloads

Defaults cap `limit` and compact long fields. Narrow `period`, set `user_id`/`group_id`, or lower `limit`. Avoid `fetch_all` on risks unless needed. Be gentle on the **demo** tenant.

## Streamable HTTP issues

Default bind is `127.0.0.1`. Remote bind exposes credentials in use — see [SECURITY.md](../SECURITY.md). Prefer stdio for desktop hosts.

## Still stuck

- Coverage / intentional gaps: `list_api_coverage` or [API.md](API.md)
- Protocol surface: [MCP.md](MCP.md)
- Issues: [GitHub Issues](https://github.com/extralabs/octowatch-mcp-server/issues)
