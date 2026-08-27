# Security policy

## Reporting a vulnerability

Please open a [GitHub Security Advisory](https://github.com/extralabs/octowatch-mcp-server/security/advisories/new) or a private report via [Issues](https://github.com/extralabs/octowatch-mcp-server/issues) if advisories are unavailable. Do not post production credentials or customer monitoring payloads in public issues.

## What this server does

`octowatch-mcp` is a **read-only** [MCP](https://modelcontextprotocol.io/) **server** for [OctoWatch DLP Cloud](https://octowatchdlp.com/). It authenticates to the Cloud API (as an HTTP client) and exposes console analytics, monitoring lists, risks, productivity, and directory reads to AI hosts (Cursor, Claude Desktop, VS Code, …).

It does **not**:

- Create, update, or delete console data (no Set\*/queue-mail/billing writes)
- Download screenshot or video **binaries** (metadata-only stream tools)
- Replace the [Web Console](https://app.octowatchdlp.com/) or product guides at [octowatchdlp.com/docs/](https://octowatchdlp.com/docs/)

## Credentials

- Defaults use the public **demo** account (`demo@octowatchdlp.com` / `demo`) so a quick local try works without a `.env`.
- For a real tenant, set `OCTOWATCH_EMAIL` / `OCTOWATCH_PASSWORD` (and optionally `OCTOWATCH_API_BASE`) via environment variables or the MCP host `env` block. See [docs/hosts.md](docs/hosts.md).
- **Never commit** production passwords to git, MCP example JSON, or chat logs.
- Prefer a **least-privilege** console operator, not a full admin, when wiring AI hosts.

## Sensitive data

Tool responses may include employee-monitoring content (activity, keystrokes snippets, mail metadata, risk hits, and similar). Treat outputs as **confidential**:

- Do not paste raw tool JSON into public channels
- Align usage with your organization’s monitoring and privacy policies
- The shared demo tenant is for evaluation only — do not assume it is private or production data

Compact mode truncates some long text fields; that is a token/UX guard, **not** a security boundary.

## Transports

- Default transport is **stdio** (host spawns the process).
- Optional `--transport streamable-http` binds to `127.0.0.1` by default. Binding to other interfaces exposes the session (and thus API credentials in use) on the network — avoid unless you understand the risk.

## Further reading

- Product: [octowatchdlp.com](https://octowatchdlp.com/)
- Product docs: [octowatchdlp.com/docs/](https://octowatchdlp.com/docs/)
- Console: [app.octowatchdlp.com](https://app.octowatchdlp.com/)
- API catalog: [app.octowatchdlp.com/api/](https://app.octowatchdlp.com/api/)
