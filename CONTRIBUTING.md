# Contributing

Thanks for helping improve **octowatch-mcp** — the read-only MCP server for [OctoWatch DLP Cloud](https://octowatchdlp.com/).

## Development setup

Requires **Python 3.10+**.

```bash
git clone https://github.com/extralabs/octowatch-mcp-server.git
cd octowatch-mcp-server
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -e ".[dev]"
cp .env.example .env   # optional; demo defaults work without it
```

Run the server:

```bash
python -m octowatch_mcp
# or: octowatch-mcp
```

## Checks

```bash
ruff check src tests
ruff format --check src tests
pytest tests/ -q
```

CI runs the same unit job on Python 3.10 and 3.12 (`OCTOWATCH_SKIP_LIVE=1`), plus a live demo smoke on `main`. Prefer keeping new tests offline-friendly unless you intentionally extend the smoke job.

## Documentation

User-facing docs live in `README.md` and `docs/`. When you change tool signatures, env vars, or tool routing:

1. Update [docs/TOOLS.md](docs/TOOLS.md) and the thin README tables
2. Keep [docs/hosts.md](docs/hosts.md) / `.env.example` in sync for config changes
3. Align when-which-tool text with `octowatch://tool-routing` / server instructions in `src/octowatch_mcp/server.py`

Do **not** paste product-site or `/api/` catalog text verbatim — link out and write MCP-specific notes. See the content boundary notes in [docs/README.md](docs/README.md).

Product links to keep current:

- https://octowatchdlp.com/
- https://octowatchdlp.com/docs/
- https://app.octowatchdlp.com/
- https://app.octowatchdlp.com/api/

## Release (maintainers)

Publishing to **PyPI** and the **official MCP Registry** is automated on a version tag. The version in `pyproject.toml` must match the tag (`0.5.1` → `v0.5.1`):

```bash
# 1) Commit + push version bump / changelog to main
# 2) Then:
git tag v0.5.1
git push origin v0.5.1
```

Workflow [`.github/workflows/publish.yml`](.github/workflows/publish.yml): Trusted Publisher → PyPI, then `mcp-publisher` via GitHub OIDC. Details: [docs/registry.md](docs/registry.md).

Directory / Marketplace discovery (no MCP hosting): [docs/distribution.md](docs/distribution.md). Cursor plugin files: [`.cursor-plugin/plugin.json`](.cursor-plugin/plugin.json), [`mcp.json`](mcp.json). Local plugin test: junction/symlink the repo to `~/.cursor/plugins/local/octowatch`, then **Developer: Reload Window**.

Update [CHANGELOG.md](CHANGELOG.md) before tagging. Keep `<!-- mcp-name: io.github.extralabs/octowatch-mcp -->` in `README.md`.
When shipping a Cursor Marketplace update, bump `version` in `.cursor-plugin/plugin.json` and re-submit at [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish).

## License

By contributing, you agree that your contributions are licensed under the MIT License — see [LICENSE](LICENSE).
