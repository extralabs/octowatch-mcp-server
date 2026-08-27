# Install & hosts

How to run **octowatch-mcp** inside common MCP hosts and how to use **your** OctoWatch login.

Product links: [octowatchdlp.com](https://octowatchdlp.com/) · [docs](https://octowatchdlp.com/docs/) · [console](https://app.octowatchdlp.com/) · [API catalog](https://app.octowatchdlp.com/api/).

## Prerequisites

- Python **3.10+** on the PATH used by the host
- Package installed: `pip install octowatch-mcp` (or editable source install)
- Network reachability to `OCTOWATCH_API_BASE` (default `https://cloud.octowatchdlp.com`)

### Host compatibility

| Host | Status |
|------|--------|
| Cursor | Expected / tested |
| Claude Desktop | Expected / tested |
| VS Code (MCP) | Expected |
| Other MCP clients | Best effort (stdio JSON-RPC) |

## PyPI install (recommended)

```bash
pip install octowatch-mcp
octowatch-mcp   # optional smoke: starts stdio server (Ctrl+C to stop)
```

## Cursor

One-click (demo credentials; run `pip install octowatch-mcp` first so `octowatch-mcp` is on PATH):

[![Install in Cursor](https://img.shields.io/badge/Cursor-Install_Server-000000?style=flat-square&logo=cursor&logoColor=white)](cursor://anysphere.cursor-deeplink/mcp/install?name=octowatch&config=eyJjb21tYW5kIjoib2N0b3dhdGNoLW1jcCIsImVudiI6eyJPQ1RPV0FUQ0hfQVBJX0JBU0UiOiJodHRwczovL2Nsb3VkLm9jdG93YXRjaGRscC5jb20iLCJPQ1RPV0FUQ0hfRU1BSUwiOiJkZW1vQG9jdG93YXRjaGRscC5jb20iLCJPQ1RPV0FUQ0hfUEFTU1dPUkQiOiJkZW1vIn19)

Manual steps:

1. Install the package (above).
2. Open Cursor MCP settings and merge a server block from:
   - Demo: [../examples/cursor-mcp-pypi.json](../examples/cursor-mcp-pypi.json)
   - Your account: [../examples/cursor-mcp-pypi-with-env.json](../examples/cursor-mcp-pypi-with-env.json)
3. Replace `YOUR_EMAIL` / `YOUR_PASSWORD` if using the with-env file.
4. Restart Cursor (or reload MCP servers).
5. In Agent chat try: *“Using OctoWatch, who am I logged in as?”*

### From source (Cursor)

Use [../examples/cursor-mcp.json](../examples/cursor-mcp.json). Set `cwd` to your clone:

- macOS/Linux: `/absolute/path/to/octowatch-mcp-server`
- Windows: `D:\\Dropbox\\VS.Code\\2026\\octowatch-mcp-server` (escape backslashes in JSON)

Prefer the venv’s `python` if the host does not inherit your shell PATH.

## Claude Desktop

1. `pip install octowatch-mcp`
2. Edit Claude Desktop MCP config (`claude_desktop_config.json`) and merge:
   - Demo: [../examples/claude-desktop-pypi.json](../examples/claude-desktop-pypi.json)
   - Your account: [../examples/claude-desktop-pypi-with-env.json](../examples/claude-desktop-pypi-with-env.json)
3. Restart Claude Desktop.
4. Confirm the `octowatch` server is connected, then ask a risks/idle question.

From source: [../examples/claude-desktop.json](../examples/claude-desktop.json) with `cwd` set like Cursor.

## VS Code

One-click (demo credentials; `pip install octowatch-mcp` first):

[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_Server-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=octowatch&config=%7B%22command%22%3A%22octowatch-mcp%22%2C%22env%22%3A%7B%22OCTOWATCH_API_BASE%22%3A%22https%3A%2F%2Fcloud.octowatchdlp.com%22%2C%22OCTOWATCH_EMAIL%22%3A%22demo%40octowatchdlp.com%22%2C%22OCTOWATCH_PASSWORD%22%3A%22demo%22%7D%7D)
[![Install in VS Code Insiders](https://img.shields.io/badge/VS_Code_Insiders-Install_Server-24bfa5?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=octowatch&config=%7B%22command%22%3A%22octowatch-mcp%22%2C%22env%22%3A%7B%22OCTOWATCH_API_BASE%22%3A%22https%3A%2F%2Fcloud.octowatchdlp.com%22%2C%22OCTOWATCH_EMAIL%22%3A%22demo%40octowatchdlp.com%22%2C%22OCTOWATCH_PASSWORD%22%3A%22demo%22%7D%7D&quality=insiders)

Or add a stdio server that runs `octowatch-mcp` (same command/env as Cursor). Exact UI paths vary by VS Code MCP support version — use the host’s “MCP: Open User Configuration” (or workspace `.vscode/mcp.json`) and paste an equivalent `command` + `env` block. See Microsoft’s MCP docs for the current schema.

## Your own login

Defaults are the **public demo** (`demo@octowatchdlp.com` / `demo`). For your company tenant:

1. Create or use a **least-privilege** console operator in the [Web Console](https://app.octowatchdlp.com/).
2. Set environment variables (prefix `OCTOWATCH_`):

| Variable | Example |
|----------|---------|
| `OCTOWATCH_EMAIL` | `operator@example.com` |
| `OCTOWATCH_PASSWORD` | *(your password)* |
| `OCTOWATCH_API_BASE` | `https://cloud.octowatchdlp.com` (or your documented `serverBase`) |

3. **Preferred for hosts:** put them in the MCP JSON `env` object (see with-env examples). The host injects them into the server process — no password in the repo.
4. **Alternative (source / local CLI):** copy [../.env.example](../.env.example) to `.env` in the process working directory (`cwd`). Do not commit `.env`.

Then call `octowatch_whoami` (or ask “who am I on OctoWatch?”) and confirm the account matches the console.

### Custom API base

Only use a publicly documented Cloud API host (`serverBase` from console config). Do not point this OSS client at undocumented internal hosts. Product and REST details: [octowatchdlp.com/docs/](https://octowatchdlp.com/docs/), [app.octowatchdlp.com/api/](https://app.octowatchdlp.com/api/).

### Demo etiquette

The demo tenant is shared. Prefer short questions over large `fetch_all` / multi-kind loops. Client-side rate limiting is on the roadmap.

## First prompts

After the server connects:

1. “Using OctoWatch, who am I logged in as?”
2. “List OctoWatch risks for the last week.”
3. “List users and groups.”

Compare aggregates in the [Web Console](https://app.octowatchdlp.com/) if something looks empty or unexpected.

## Streamable HTTP (optional)

```bash
octowatch-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

Defaults to localhost. Binding elsewhere exposes the live session — see [SECURITY.md](../SECURITY.md).

## ChatGPT and other hosts

There is **no** checked-in ChatGPT-specific JSON example. Many ChatGPT / cloud-agent setups expect a **remote** MCP URL (connectors), not a local `command` like Cursor/Claude Desktop.

Practical options today:

1. Use **Cursor**, **Claude Desktop**, or **VS Code** with the stdio examples in this doc (best path for `octowatch-mcp`).
2. If your host documents custom MCP over HTTP, run Streamable HTTP locally (above) and register `http://127.0.0.1:8000/mcp` only as that host allows — keep bind on localhost unless you understand the risk.

When a stable public ChatGPT connector schema exists, we can add an `examples/` file; until then treat ChatGPT as host-dependent.

## Next

- Tool routing & args: [TOOLS.md](TOOLS.md)
- Protocol / prompts: [MCP.md](MCP.md)
- Problems: [troubleshooting.md](troubleshooting.md)
