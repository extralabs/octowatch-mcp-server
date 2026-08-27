# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- SEO / discovery: richer PyPI keywords & classifiers; README H1 + lead use **OctoWatch DLP** / `octowatchdlp.com` (brand disambiguation); align Registry / Cursor plugin blurbs; Homepage / websiteUrl stay on the **product** site (`octowatchdlp.com`).
- [docs/distribution.md](docs/distribution.md): GitHub About checklist (Website was empty — critical for crawlers) + [`scripts/sync-github-about.ps1`](scripts/sync-github-about.ps1).

### Added

- CI: after PyPI on tag `v*`, publish to the official MCP Registry via `mcp-publisher` + GitHub OIDC ([`.github/workflows/publish.yml`](.github/workflows/publish.yml)).
- Cursor plugin manifest ([`.cursor-plugin/plugin.json`](.cursor-plugin/plugin.json), [`mcp.json`](mcp.json)) with Configure variables for email/password.
- [docs/distribution.md](docs/distribution.md): directory rollout, auth for catalogs, deferred hosted channels (Smithery / remote Connectors).
- README: **Where to find us** + clearer demo vs tenant credentials.
- Directory submits recorded: [Glama](https://glama.ai/), [mcpservers.org](https://mcpservers.org/), [mcpfind.org](https://mcpfind.org/), [mcpmarket.com](https://mcpmarket.com/); mcp.so skipped (paid).
- Open Plugins: root [`.mcp.json`](../.mcp.json) for [cursor.directory](https://cursor.directory) auto-detect (must be on GitHub `main`).

## [0.5.1] - 2026-08-27

### Added

- Official MCP Registry prep: [`server.json`](server.json), `<!-- mcp-name: io.github.extralabs/octowatch-mcp -->` in README, [docs/registry.md](docs/registry.md).

### Changed

- Documentation restructure: README funnel, `docs/` index, host install + credentials walkthrough, tool reference, security and contributing guides (MCP-focused; product docs and `/api/` remain canonical for console/REST).
- README: MCP badge; one-click Cursor / VS Code install badges (demo env); ChatGPT/other-hosts notes.

## [0.5.0] - 2026-08

### Breaking

- Tool failures return MCP `is_error=True` via `ToolError` instead of a successful JSON payload with an `"error"` key.

### Added

- `read_only_hint` / titles on all tools (host auto-approve friendly)
- Map API and validation failures to `ToolError`
- Richer input `Field` descriptions on common period/filter params
- Log to stderr (stdio-safe)
- Resources: `octowatch://coverage`, `octowatch://tool-routing`, `octowatch://whoami`
- Prompts: `daily_risks_brief`, `idle_review`, `user_activity_drilldown`, `monitoring_keyword_hunt`
- Structured returns for **all** tools (`structured_content`; lists wrapped as `{"data": ...}`)
- `OCTOWATCH_TOOLSETS=all|core|console` (console auto-includes core)
- Optional `--transport streamable-http` (default bind `127.0.0.1`)
- In-process MCP protocol tests; ruff in CI
- Docs: [docs/MCP.md](docs/MCP.md)

## Pre-0.5.0

Earlier alpha iterations (tool coverage expansion, packaging, CI) shipped before this changelog format. Start from **0.5.0** for documented breaking behavior around errors and protocol features.

<!-- Compare/release footer links: add after git tag v0.5.0 exists on the remote.
[Unreleased]: https://github.com/extralabs/octowatch-mcp-server/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/extralabs/octowatch-mcp-server/releases/tag/v0.5.0
-->
