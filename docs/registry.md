# Official MCP Registry

How maintainers list **octowatch-mcp** in the [official MCP Registry](https://registry.modelcontextprotocol.io/) (Anthropic / Model Context Protocol).

**Do not** open a pull request that adds YAML/JSON under `modelcontextprotocol/registry` (`/servers` or `data/`). That workflow is deprecated; such PRs are closed. Publish with the [`mcp-publisher`](https://modelcontextprotocol.io/registry/quickstart) CLI (or CI) instead.

## Automated release (recommended)

Do **not** publish on every Cursor Commit + Sync — that would spam PyPI and the registry. Release is triggered by a **version tag**.

Already wired in [`.github/workflows/publish.yml`](../.github/workflows/publish.yml):

1. Tag `vX.Y.Z` → build → **PyPI** (Trusted Publisher)
2. Same job → **MCP Registry** via `mcp-publisher login github-oidc` (no local CLI, no PAT)

### Your release steps in Cursor

1. Bump `version` in `pyproject.toml` (and preferably in `server.json`; CI also rewrites `server.json` from the tag).
2. Keep `<!-- mcp-name: io.github.extralabs/octowatch-mcp -->` in `README.md`.
3. Update `CHANGELOG.md`.
4. **Commit + Sync** to `main`.
5. Create and push the tag (one extra step — not every commit):

```bash
git tag v0.5.2
git push origin v0.5.2
```

Or in GitHub: **Releases → Draft a new release →** tag `v0.5.2`.

Watch **Actions → Publish**. When green, check:

- https://pypi.org/project/octowatch-mcp/
- https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.extralabs/octowatch-mcp

OIDC auth needs `permissions.id-token: write` (already set). No registry secrets required for `github-oidc` under namespace `io.github.extralabs/...`.

## Manual publish (optional)

If CI is down, or you need a one-off:

1. Ensure the matching version is already on PyPI (README includes the `mcp-name` comment).
2. Install [`mcp-publisher`](https://github.com/modelcontextprotocol/registry/releases), then:

```bash
mcp-publisher login github
mcp-publisher publish
```

### Install `mcp-publisher` (Windows)

```powershell
$arch = if ([System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture -eq "Arm64") { "arm64" } else { "amd64" }
Invoke-WebRequest -Uri "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_windows_$arch.tar.gz" -OutFile "mcp-publisher.tar.gz"
tar xf mcp-publisher.tar.gz mcp-publisher.exe
# Move mcp-publisher.exe onto PATH, then:
mcp-publisher --help
```

## Files in this repo

| File | Role |
|------|------|
| [`server.json`](../server.json) | Registry metadata (name, PyPI package, env vars) |
| [`README.md`](../README.md) | Must contain `<!-- mcp-name: io.github.extralabs/octowatch-mcp -->` (ownership proof on PyPI) |

Registry name: **`io.github.extralabs/octowatch-mcp`**.

## References

- [Automate with GitHub Actions](https://modelcontextprotocol.io/registry/github-actions)
- [Quickstart](https://modelcontextprotocol.io/registry/quickstart)
- [Package types (PyPI ownership)](https://modelcontextprotocol.io/registry/package-types)
- [Authentication / namespaces](https://modelcontextprotocol.io/registry/authentication)
