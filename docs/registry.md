# Official MCP Registry

How maintainers list **octowatch-mcp** in the [official MCP Registry](https://registry.modelcontextprotocol.io/) (Anthropic / Model Context Protocol).

**Do not** open a pull request that adds YAML/JSON under `modelcontextprotocol/registry` (`/servers` or `data/`). That workflow is deprecated; such PRs are closed. Publish with the [`mcp-publisher`](https://modelcontextprotocol.io/registry/quickstart) CLI instead.

## Files in this repo

| File | Role |
|------|------|
| [`server.json`](../server.json) | Registry metadata (name, PyPI package, env vars) |
| [`README.md`](../README.md) | Must contain `<!-- mcp-name: io.github.extralabs/octowatch-mcp -->` (ownership proof on PyPI) |

Registry name: **`io.github.extralabs/octowatch-mcp`** (GitHub org namespace). Login must be an account that can act for [`extralabs`](https://github.com/extralabs).

## Prerequisites

1. Version on PyPI matches `server.json` / `pyproject.toml` (Trusted Publisher tag release).
2. That PyPI release’s README includes the `mcp-name` HTML comment above (registry fetches description from pypi.org).
3. [`mcp-publisher`](https://github.com/modelcontextprotocol/registry/releases) installed and on `PATH`.

### Install `mcp-publisher` (Windows)

```powershell
$arch = if ([System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture -eq "Arm64") { "arm64" } else { "amd64" }
Invoke-WebRequest -Uri "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_windows_$arch.tar.gz" -OutFile "mcp-publisher.tar.gz"
tar xf mcp-publisher.tar.gz mcp-publisher.exe
# Move mcp-publisher.exe onto PATH, then:
mcp-publisher --help
```

macOS/Linux: see [Registry quickstart](https://modelcontextprotocol.io/registry/quickstart).

## Publish flow

After tagging a PyPI release that includes the `mcp-name` comment:

```bash
# Keep versions in sync
# pyproject.toml, server.json → same X.Y.Z as the PyPI artifact

mcp-publisher login github
mcp-publisher validate   # if available; else publish will validate
mcp-publisher publish
```

Verify:

```bash
curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.extralabs/octowatch-mcp"
```

## Version bumps

On each release that should appear in the registry:

1. Bump `version` in `pyproject.toml` and both `version` fields in `server.json` (top-level and `packages[0]`).
2. Tag / push so PyPI Trusted Publisher ships the wheel + README.
3. Run `mcp-publisher publish` again (or automate via [GitHub Actions](https://modelcontextprotocol.io/registry/github-actions)).

## References

- [Quickstart](https://modelcontextprotocol.io/registry/quickstart)
- [Package types (PyPI ownership)](https://modelcontextprotocol.io/registry/package-types)
- [Authentication / namespaces](https://modelcontextprotocol.io/registry/authentication)
