"""In-process MCP protocol smoke tests (no live Cloud API)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from mcp import Client

from octowatch_mcp.client import OctoWatchAPIError
from octowatch_mcp.server import mcp


def _content_text(result) -> str:
    return " ".join(block.text for block in result.content if hasattr(block, "text"))


def _list_tools():
    async def _go():
        async with Client(mcp) as client:
            result = await client.list_tools()
            return list(result.tools)

    return asyncio.run(_go())


def test_list_tools_all_read_only():
    tools = _list_tools()
    assert len(tools) >= 20
    missing = [
        t.name for t in tools if t.annotations is None or t.annotations.read_only_hint is not True
    ]
    assert missing == [], f"tools missing read_only_hint=True: {missing}"


def test_list_tools_have_titles():
    tools = _list_tools()
    untitled = [t.name for t in tools if not (t.title or "").strip()]
    assert untitled == [], f"tools missing title: {untitled}"


def test_validation_error_is_tool_error():
    async def _go():
        async with Client(mcp) as client:
            return await client.call_tool(
                "get_day_structure",
                {"mode": "detail", "period": "today"},
            )

    result = asyncio.run(_go())
    assert result.is_error is True
    assert "user_id" in _content_text(result).lower()


def test_bad_period_is_tool_error():
    async def _go():
        async with Client(mcp) as client:
            return await client.call_tool(
                "list_risks",
                {"period": "last_millennium"},
            )

    result = asyncio.run(_go())
    assert result.is_error is True
    text = _content_text(result).lower()
    assert "period" in text or "unknown" in text


def test_api_error_mapped_to_tool_error():
    mock_client = MagicMock()
    mock_client.ensure_auth.side_effect = OctoWatchAPIError("auth failed", status_code=401)

    async def _go():
        with patch("octowatch_mcp.server._get_client", return_value=mock_client):
            async with Client(mcp) as client:
                return await client.call_tool("octowatch_whoami", {})

    result = asyncio.run(_go())
    assert result.is_error is True
    text = _content_text(result)
    assert "401" in text or "auth" in text.lower()


def test_all_tools_advertise_object_output_schema():
    tools = _list_tools()
    missing = [t.name for t in tools if not t.output_schema]
    assert missing == [], f"tools without output_schema: {missing}"
    bad = [t.name for t in tools if t.output_schema and t.output_schema.get("type") != "object"]
    assert bad == [], f"output_schema must be object: {bad}"


def test_list_api_coverage_structured():
    async def _go():
        async with Client(mcp) as client:
            return await client.call_tool("list_api_coverage", {})

    result = asyncio.run(_go())
    assert result.is_error is False
    assert isinstance(result.structured_content, dict)
    assert result.structured_content


def test_list_resources_and_prompts():
    async def _go():
        async with Client(mcp) as client:
            resources = await client.list_resources()
            prompts = await client.list_prompts()
            return resources, prompts

    resources, prompts = asyncio.run(_go())
    uris = {str(r.uri) for r in resources.resources}
    assert "octowatch://coverage" in uris
    assert "octowatch://tool-routing" in uris
    assert "octowatch://whoami" in uris
    names = {p.name for p in prompts.prompts}
    assert {
        "daily_risks_brief",
        "idle_review",
        "user_activity_drilldown",
        "monitoring_keyword_hunt",
    } <= names


def test_read_coverage_resource():
    async def _go():
        async with Client(mcp) as client:
            return await client.read_resource("octowatch://coverage")

    result = asyncio.run(_go())
    body = ""
    for block in result.contents:
        if hasattr(block, "text") and block.text:
            body = block.text
            break
    assert "covered" in body.lower() or "out_of_scope" in body


def test_toolsets_catalog_matches_registered_tools():
    """Prevent drift: every registered tool must be in CORE or CONSOLE."""
    from octowatch_mcp.toolsets import ALL_TOOLS

    tools = _list_tools()
    names = {t.name for t in tools}
    missing_from_catalog = names - ALL_TOOLS
    orphan_catalog = ALL_TOOLS - names
    assert missing_from_catalog == set(), f"Add to toolsets.py: {missing_from_catalog}"
    assert orphan_catalog == set(), f"Remove from toolsets.py: {orphan_catalog}"
