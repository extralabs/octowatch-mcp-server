"""Live smoke against demo Cloud (skipped if OCTOWATCH_SKIP_LIVE=1)."""

from __future__ import annotations

import os

import pytest

from octowatch_mcp.client import OctoWatchClient
from octowatch_mcp.filters import users_filter_for_group


@pytest.mark.skipif(os.getenv("OCTOWATCH_SKIP_LIVE") == "1", reason="live API skipped")
def test_demo_login_and_risks() -> None:
    with OctoWatchClient() as client:
        login = client.login()
        assert login.get("Token")
        tree = client.get_users_groups()
        assert tree.get("Items")
        risks = client.risks()
        assert "List" in risks


@pytest.mark.skipif(os.getenv("OCTOWATCH_SKIP_LIVE") == "1", reason="live API skipped")
def test_demo_monitoring_and_chrono() -> None:
    with OctoWatchClient() as client:
        client.login()
        apps = client.monitoring("Apps", num_rows=5)
        assert isinstance(apps, dict)
        chrono = client.chrono(num_rows=5)
        assert isinstance(chrono, dict)
        # Group filter NodeType=14 must be accepted (HTTP 200 even if empty List)
        filt = users_filter_for_group(1)
        assert filt[0]["NodeType"] == 14
        prod = client.productivity(users_filter=filt)
        assert isinstance(prod, dict)
