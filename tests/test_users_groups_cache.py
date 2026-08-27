"""Session cache for GetUsersGroups2."""

from __future__ import annotations

from octowatch_mcp.client import OctoWatchClient
from octowatch_mcp.config import Settings


def test_users_groups_cached_until_refresh() -> None:
    client = OctoWatchClient(
        Settings(api_base="https://example.test", email="a@b.c", password="x")
    )
    calls = {"n": 0}

    def fake_get(path: str, **kwargs):
        calls["n"] += 1
        assert path == "/api/Edit/GetUsersGroups2"
        return {"Items": [{"ID": calls["n"]}]}

    client.get = fake_get  # type: ignore[method-assign]
    client.ensure_auth = lambda: None  # type: ignore[method-assign]

    a = client.get_users_groups()
    b = client.get_users_groups()
    assert a is b
    assert calls["n"] == 1

    c = client.get_users_groups(force_refresh=True)
    assert calls["n"] == 2
    assert c["Items"][0]["ID"] == 2

    d = client.get_directory("users_groups")
    assert d is c
    assert calls["n"] == 2


def test_login_invalidates_users_groups_cache() -> None:
    client = OctoWatchClient(
        Settings(api_base="https://example.test", email="a@b.c", password="x")
    )
    client._users_groups_cache = {"Items": []}
    client._users_groups_cached_at = 1.0
    client.invalidate_users_groups_cache()
    assert client._users_groups_cache is None
