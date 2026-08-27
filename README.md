# OctoWatch DLP MCP Server

PyPI package: [`octowatch-mcp`](https://pypi.org/project/octowatch-mcp/) · product: [octowatchdlp.com](https://octowatchdlp.com/) (not related to other products named “OctoWatch”).

[![PyPI](https://img.shields.io/pypi/v/octowatch-mcp.svg)](https://pypi.org/project/octowatch-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/octowatch-mcp.svg)](https://pypi.org/project/octowatch-mcp/)
[![CI](https://github.com/extralabs/octowatch-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/extralabs/octowatch-mcp-server/actions/workflows/ci.yml)
[![MCP](https://img.shields.io/badge/MCP-server-6001D2)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[![Install in Cursor](https://img.shields.io/badge/Cursor-Install_Server-000000?style=flat-square&logo=cursor&logoColor=white)](cursor://anysphere.cursor-deeplink/mcp/install?name=octowatch&config=eyJjb21tYW5kIjoib2N0b3dhdGNoLW1jcCIsImVudiI6eyJPQ1RPV0FUQ0hfQVBJX0JBU0UiOiJodHRwczovL2Nsb3VkLm9jdG93YXRjaGRscC5jb20iLCJPQ1RPV0FUQ0hfRU1BSUwiOiJkZW1vQG9jdG93YXRjaGRscC5jb20iLCJPQ1RPV0FUQ0hfUEFTU1dPUkQiOiJkZW1vIn19)
[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_Server-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=octowatch&config=%7B%22command%22%3A%22octowatch-mcp%22%2C%22env%22%3A%7B%22OCTOWATCH_API_BASE%22%3A%22https%3A%2F%2Fcloud.octowatchdlp.com%22%2C%22OCTOWATCH_EMAIL%22%3A%22demo%40octowatchdlp.com%22%2C%22OCTOWATCH_PASSWORD%22%3A%22demo%22%7D%7D)
[![Install in VS Code Insiders](https://img.shields.io/badge/VS_Code_Insiders-Install_Server-24bfa5?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=octowatch&config=%7B%22command%22%3A%22octowatch-mcp%22%2C%22env%22%3A%7B%22OCTOWATCH_API_BASE%22%3A%22https%3A%2F%2Fcloud.octowatchdlp.com%22%2C%22OCTOWATCH_EMAIL%22%3A%22demo%40octowatchdlp.com%22%2C%22OCTOWATCH_PASSWORD%22%3A%22demo%22%7D%7D&quality=insiders)

Read-only [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for **[OctoWatch DLP Cloud](https://octowatchdlp.com/)** employee monitoring and data-loss prevention — ask Cursor, Claude, or VS Code about risks, idle time, productivity, and monitoring in plain language.

<!-- mcp-name: io.github.extralabs/octowatch-mcp -->

- Product: [octowatchdlp.com](https://octowatchdlp.com/)
- Product docs: [octowatchdlp.com/docs/](https://octowatchdlp.com/docs/)
- Web Console: [app.octowatchdlp.com](https://app.octowatchdlp.com/)
- In-app API catalog: [app.octowatchdlp.com/api/](https://app.octowatchdlp.com/api/)

Python MCP SDK **v2** (`MCPServer`). Built for SecOps and managers — open-source companion to the OctoWatch console.

**Contents:** [Status](#status) · [Where to find us](#where-to-find-us) · [Prerequisites](#prerequisites) · [Example questions](#example-questions) · [Security](#security--privacy) · [Limitations](#limitations) · [Quick start](#quick-start-pypi) · [Your account](#your-account-email--password) · [Tools](#core-tools) · [Configuration](#configuration) · [Documentation](#documentation) · [Contributing](#contributing)

## Status

**Alpha** (`v0.5.1`). APIs and tool shapes may change; pin a PyPI version in production configs.

Tool failures return MCP `is_error` (`ToolError`). All tools advertise `read_only_hint`.

## Where to find us

The MCP runs **locally** (no ExtrLabs-hosted MCP). Catalogs point at PyPI / GitHub; you supply Cloud login via env.

| Channel | Link |
|---------|------|
| PyPI | [octowatch-mcp](https://pypi.org/project/octowatch-mcp/) |
| Official MCP Registry | [`io.github.extralabs/octowatch-mcp`](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.extralabs/octowatch-mcp) |
| GitHub | [extralabs/octowatch-mcp-server](https://github.com/extralabs/octowatch-mcp-server) |
| Cursor Marketplace | Plugin manifest [`.cursor-plugin`](.cursor-plugin/plugin.json) — [publish form](https://cursor.com/marketplace/publish) (manual review) |
| Directories | [Glama](https://glama.ai/) · [mcpservers.org](https://mcpservers.org/) · [mcpfind.org](https://mcpfind.org/) · [mcpmarket.com](https://mcpmarket.com/) · [PulseMCP](https://www.pulsemcp.com/) · [awesome-mcp-servers#13003](https://github.com/punkpeye/awesome-mcp-servers/pull/13003) (mcp.so skipped — paid) |
| cursor.directory | Open Plugins: root [`.mcp.json`](.mcp.json) + [`.cursor-plugin/plugin.json`](.cursor-plugin/plugin.json) — re-submit after these are on `main` |

Directory / Marketplace maintainer notes: [docs/distribution.md](docs/distribution.md).

## Prerequisites

- Python **3.10+**
- An MCP-capable host (Cursor, Claude Desktop, VS Code, …)
- Network access to your Cloud API host (default `https://cloud.octowatchdlp.com`)

## Example questions

- “Which **Risks** in the last day?”
- “Who was idle the longest yesterday?”
- “Productivity summary for Accounting”
- “Show Monitoring keystrokes for Emily”
- “Find keyword `invoice` across monitoring last week”
- “List users and groups”

### Short scenarios

| Goal | Ask something like… |
|------|---------------------|
| DLP / policy hits | “Summarize risks for today by user and rule” |
| Idle time (not formal alerts) | “Who was idle more than 2 hours yesterday?” |
| Top apps/sites | “Top applications for group Accounting last 7 days” |
| Keyword hunt | “Search monitoring for `confidential` last 30 days” |
| Directory | “List users and groups, then show info for AliasID 4” |

## Security & privacy

> Defaults use the public **demo** account.  
> **Do not put production passwords in MCP config or git.** Use env vars and a least-privilege console operator.  
> No writes, no screenshot/video binary downloads.

Monitoring responses can contain sensitive employee data (activity, keystrokes snippets, mail metadata). Treat tool output as confidential. Full policy: [SECURITY.md](SECURITY.md).

## Limitations

- **Read-only** — not a full console replacement ([Web Console](https://app.octowatchdlp.com/))
- No screenshot/video **binary** downloads (stream **metadata** only)
- Not a mirror of product docs or the REST catalog — those stay at [docs](https://octowatchdlp.com/docs/) and [/api/](https://app.octowatchdlp.com/api/)
- Alpha — expect breaking changes between minors until 1.0

## Quick start (PyPI)

Use the **Install** badges at the top of this README (Cursor / VS Code; demo credentials). First ensure the CLI is available:

```bash
pip install octowatch-mcp
```

Or configure manually — example for Cursor / Claude-style `mcpServers` (demo credentials):

```json
{
  "mcpServers": {
    "octowatch": {
      "command": "octowatch-mcp",
      "env": {
        "OCTOWATCH_API_BASE": "https://cloud.octowatchdlp.com",
        "OCTOWATCH_EMAIL": "demo@octowatchdlp.com",
        "OCTOWATCH_PASSWORD": "demo"
      }
    }
  }
}
```

Ready-made files: [examples/cursor-mcp-pypi.json](examples/cursor-mcp-pypi.json), [examples/claude-desktop-pypi.json](examples/claude-desktop-pypi.json). Per-host steps: [docs/hosts.md](docs/hosts.md).

Restart the host, then try: *“Using OctoWatch, who am I logged in as?”* or *“List risks for the last week.”*

Demo credentials work without a `.env`. Be gentle with the shared demo tenant (avoid aggressive agent loops).

### From source

```bash
git clone https://github.com/extralabs/octowatch-mcp-server.git
cd octowatch-mcp-server
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .
cp .env.example .env   # optional
python -m octowatch_mcp
```

Use [examples/cursor-mcp.json](examples/cursor-mcp.json) / [examples/claude-desktop.json](examples/claude-desktop.json) and set `cwd` to your clone (Windows: `D:\\path\\to\\octowatch-mcp-server`).

### ChatGPT and other hosts

There is **no** single public ChatGPT JSON config we ship yet — ChatGPT / similar products often use **remote** MCP connectors rather than a local `command` stdio process.

- For local desktop agents, prefer **Cursor**, **Claude Desktop**, or **VS Code** with the examples above.
- If your host supports custom MCP over HTTP, you can run `octowatch-mcp --transport streamable-http` (localhost only by default) and register that endpoint per the host’s docs — see [docs/hosts.md](docs/hosts.md#chatgpt-and-other-hosts).

## Your account (email / password)

OctoWatch Cloud still needs a console login. The MCP does **not** store passwords for you — the host passes them as process env.

| Mode | What to set |
|------|-------------|
| **Demo (try-out)** | Defaults / Install badges: `demo@octowatchdlp.com` / `demo` |
| **Your tenant** | Your least-privilege operator email + password in MCP `env` (or Cursor plugin **Configure**) |

| Variable | Meaning |
|----------|---------|
| `OCTOWATCH_EMAIL` | Console operator email |
| `OCTOWATCH_PASSWORD` | Console password (`isSecret` in Registry metadata) |
| `OCTOWATCH_API_BASE` | Cloud API host if not the default public cloud |

**Recommended:** put them in the MCP host JSON `env` block — [examples/cursor-mcp-pypi-with-env.json](examples/cursor-mcp-pypi-with-env.json) / [examples/claude-desktop-pypi-with-env.json](examples/claude-desktop-pypi-with-env.json). Cursor plugin variables: [`.cursor-plugin/plugin.json`](.cursor-plugin/plugin.json).

Alternatively, for a source install, copy `.env.example` → `.env` next to the process working directory.

Never commit real passwords. Verify the same data in the [Web Console](https://app.octowatchdlp.com/). Walkthrough: [docs/hosts.md](docs/hosts.md#your-own-login).

## Core tools

| Tool | Cloud area | Notes |
|------|------------|--------|
| `octowatch_whoami` | Auth session | Account / host (no password) |
| `list_users_groups` | Directory tree | Type 0 root, 1 group, 2 user |
| `list_risks` | Risks + Analytics | Default `mode=summary` |
| `list_anomalies` | Alerts | Formal deviations (not idle) |
| `get_idle_summary` | Productivity | Rank by `InactiveTime` |
| `get_activity_summary` | Activity | Top apps/sites |
| `get_timesheet` | TimeSheet | Worked vs expected hours |
| `get_productivity_summary` | Productivity + analytics | Per-user rollup |
| `list_reports` | Reports | Scheduled + processing tasks |

## Console coverage tools

| Tool | Cloud area | Notes |
|------|------------|--------|
| `get_analytics` | Analytics | `view=overall\|disciplina\|activity\|productivity` |
| `get_dashboard` | Dashboard | Widgets; blobs stripped |
| `get_chrono` | Chrono | Timeline |
| `get_day_structure` | Day structure | `list` or `detail` |
| `list_monitoring` | Monitoring | One kind; compact by default |
| `search_monitoring` | Tools → Search | `filter_key` across kinds |
| `get_activity_detail` | Activity window | Drill-down |
| `list_online` | Live | Presence only |
| `list_stream_meta` | Stream | Metadata only |
| `list_directory` | Edit Get\* | users/groups/computers/… |
| `get_user_info` | User card | AliasID / computer |
| `get_account_readonly` | Account Get\* | No Set\*/PIN |
| `list_api_coverage` | (static) | Gap summary |

Full arguments, routing, and scenarios: [docs/TOOLS.md](docs/TOOLS.md).  
MCP prompts/resources: [docs/MCP.md](docs/MCP.md).

## Configuration

| Env | Default | Meaning |
|-----|---------|---------|
| `OCTOWATCH_API_BASE` | `https://cloud.octowatchdlp.com` | API host (`serverBase`) |
| `OCTOWATCH_EMAIL` | `demo@octowatchdlp.com` | Console operator |
| `OCTOWATCH_PASSWORD` | `demo` | **Demo only** by default |
| `OCTOWATCH_DEFAULT_DAYS` | `1` | Lookback when tools omit dates/period |
| `OCTOWATCH_TOOLSETS` | `all` | `all` \| `core` \| `console` (console includes core) |

```bash
octowatch-mcp                                      # stdio (default)
octowatch-mcp --transport streamable-http          # http://127.0.0.1:8000/mcp
```

### Periods & filters

Prefer `period=today|yesterday|last_7_days|last_30_days`, or `date_from` / `date_to`.

- Date-only values cover the **full calendar day** (`date_to` → `23:59:59`).
- Optional `user_id` (AliasID) and `group_id` on most read tools.
- POST body `TreeviewUsers`: all → `NodeType=-666666`; **group → `NodeType=14`**; **user → `NodeType=1`**.

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/README.md](docs/README.md) | Doc index |
| [docs/hosts.md](docs/hosts.md) | Install per host + your login |
| [docs/TOOLS.md](docs/TOOLS.md) | Tool reference + when-which |
| [docs/MCP.md](docs/MCP.md) | Protocol, resources, prompts |
| [docs/API.md](docs/API.md) | MCP coverage audit (not a full REST mirror) |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common failures |
| [docs/registry.md](docs/registry.md) | Official MCP Registry (`server.json`) |
| [docs/distribution.md](docs/distribution.md) | Directories, Marketplace, deferred hosted channels |

### Product & console

- [octowatchdlp.com](https://octowatchdlp.com/)
- [octowatchdlp.com/docs/](https://octowatchdlp.com/docs/)
- [app.octowatchdlp.com](https://app.octowatchdlp.com/)
- [app.octowatchdlp.com/api/](https://app.octowatchdlp.com/api/)

## Roadmap

Planned (not scheduled): tighter payload budgets, client-side rate limits, argument completions, server icon, optional MCP Apps UI, tool-routing evals. Registry metadata: [docs/registry.md](docs/registry.md). Protocol surface: [docs/MCP.md](docs/MCP.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Changelog: [CHANGELOG.md](CHANGELOG.md). Issues: [GitHub Issues](https://github.com/extralabs/octowatch-mcp-server/issues).

## License

MIT — see [LICENSE](LICENSE).
