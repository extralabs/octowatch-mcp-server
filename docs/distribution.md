# Distribution & directories (no MCP hosting)

How **octowatch-mcp** is discovered and installed. The MCP process always runs **on the user’s machine** (`stdio` via PyPI / `uvx`). It authenticates to existing **OctoWatch Cloud** with console email/password. We do **not** host a public remote MCP endpoint.

## Auth model for catalogs

| Mode | Credentials | Notes |
|------|-------------|--------|
| Try-out | `demo@octowatchdlp.com` / `demo` | Shared public demo; be gentle with agent loops |
| Your tenant | `OCTOWATCH_EMAIL` + `OCTOWATCH_PASSWORD` | Least-privilege operator; set in host MCP `env` or plugin Configure UI |
| Secrets | Never in git | Password is `isSecret` in [`server.json`](../server.json); plugin uses `${OCTOWATCH_PASSWORD}` placeholders only |

Hosts substitute env / plugin variables locally. Passwords are not sent to ExtrLabs for MCP install.

## Live listings

| Channel | Role | Status / action |
|---------|------|-----------------|
| [PyPI `octowatch-mcp`](https://pypi.org/project/octowatch-mcp/) | Install artifact | Publish on tag `v*` ([`publish.yml`](../.github/workflows/publish.yml)) |
| [Official MCP Registry](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.extralabs/octowatch-mcp) `io.github.extralabs/octowatch-mcp` | Canonical metadata | Same tag job; see [registry.md](registry.md) |
| GitHub topics | Discovery crawlers | `mcp`, `mcp-server`, `model-context-protocol`, `dlp`, `employee-monitoring`, `python`, `security`, `octowatch` |
| [PulseMCP](https://www.pulsemcp.com/) | Directory (often syncs Registry) | Submissions paused mid-Aug 2026; re-check search for `octowatch` after ingestion resumes |
| [Glama](https://glama.ai/) | Directory + score badges | **Submitted** (2026-08-27); claim listing when card appears; topics help auto-index |
| [mcpservers.org](https://mcpservers.org/) | Awesome MCP Servers directory | **Submitted** (2026-08-27) |
| [mcpfind.org](https://mcpfind.org/) | MCP Find directory | **Submitted** (2026-08-27) |
| [mcpmarket.com](https://mcpmarket.com/) | MCP Market directory | **Submitted** (2026-08-27) |
| [mcp.so](https://mcp.so/) | Directory | **Skipped for now** (paid listing) |
| [cursor.directory](https://cursor.directory) | Community Cursor listing | Needs **pushed** root [`.mcp.json`](../.mcp.json) (Open Plugins). Re-submit at [plugins/new](https://cursor.directory/plugins/new) after push. |
| [Cursor Marketplace](https://cursor.com/marketplace) | Curated plugins | Manifest: [`.cursor-plugin/plugin.json`](../.cursor-plugin/plugin.json) + [`mcp.json`](../mcp.json); submit at [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish) |
| [awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) | Curated GitHub list | PR under **Security**: [#13003](https://github.com/punkpeye/awesome-mcp-servers/pull/13003) |

Blurb for forms (keep identical):

> Read-only OctoWatch DLP Cloud MCP; runs locally; demo credentials or your console login.

## Deferred (needs hosting or heavy packaging)

Do **not** pursue until product decides to host a remote MCP:

| Channel | Why deferred |
|---------|----------------|
| [Smithery](https://smithery.ai/) | Hosted HTTP MCP required |
| Claude Connectors Directory | Remote MCP preferred; review + hosted endpoint |
| Anthropic `.mcpb` Desktop bundle | No ExtrLabs host, but separate Python/runtime packaging |
| Public `streamable-http` on our infra | Explicit self-host of MCP |

Local `octowatch-mcp --transport streamable-http` on **localhost** remains fine for personal experiments ([hosts.md](hosts.md)); that is not a public listing.

## Maintainer checklist (each discovery push)

1. Confirm Registry + PyPI version match.
2. Topics still set on GitHub (`gh api repos/extralabs/octowatch-mcp-server/topics`).
3. Confirm Glama / mcpservers.org / mcpfind.org / mcpmarket.com cards went live; claim Glama if needed. Skip **mcp.so** while listing is paid.
4. **cursor.directory** scans GitHub `HEAD` for Open Plugins components ([parser](https://github.com/cursor/community-plugins)): root `.mcp.json` or `mcp.json`, plus optional `.cursor-plugin/plugin.json`. Files must be **pushed** before [plugins/new](https://cursor.directory/plugins/new) works. Helper: [`scripts/open-directory-submits.ps1`](../scripts/open-directory-submits.ps1).
5. Cursor Marketplace: after plugin changes, re-submit for review. Local smoke: junction/symlink repo → `~/.cursor/plugins/local/octowatch`, then **Developer: Reload Window**.
6. Update the “Where to find us” table in [README.md](../README.md) when a new card goes live.

### Open Plugins layout (cursor.directory)

| Path | Role |
|------|------|
| [`.mcp.json`](../.mcp.json) | Discovery config with **demo** env (what cursor.directory indexes) |
| [`mcp.json`](../mcp.json) | Cursor Marketplace / plugin `${VAR}` placeholders |
| [`.cursor-plugin/plugin.json`](../.cursor-plugin/plugin.json) | Marketplace manifest + variables schema |

### Form fields (copy-paste)

| Field | Value |
|-------|--------|
| GitHub URL | `https://github.com/extralabs/octowatch-mcp-server` |
| Name | OctoWatch DLP / `octowatch-mcp` |
| Description | Read-only OctoWatch DLP Cloud MCP; runs locally; demo credentials or your console login. |
| Tags | `mcp`, `dlp`, `security`, `monitoring`, `python` |
| Install | `uvx octowatch-mcp` or `pip install octowatch-mcp` |
| Env | `OCTOWATCH_EMAIL`, `OCTOWATCH_PASSWORD` (secret), optional `OCTOWATCH_API_BASE` |
| Registry | `io.github.extralabs/octowatch-mcp` |
