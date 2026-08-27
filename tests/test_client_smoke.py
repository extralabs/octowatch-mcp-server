"""Live smoke against demo Cloud (skipped if OCTOWATCH_SKIP_LIVE=1)."""

from __future__ import annotations

import os

import pytest

from octowatch_mcp.client import OctoWatchClient


@pytest.mark.skipif(os.getenv("OCTOWATCH_SKIP_LIVE") == "1", reason="live API skipped")
def test_demo_login_and_risks() -> None:
    with OctoWatchClient() as client:
        login = client.login()
        assert login.get("Token")
        tree = client.get_users_groups()
        assert tree.get("Items")
        risks = client.risks()
        assert "List" in risks
