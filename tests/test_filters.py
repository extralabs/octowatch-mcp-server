"""Filter builder unit tests."""

from __future__ import annotations

from octowatch_mcp.compact import compact_api_payload
from octowatch_mcp.filters import (
    NODE_ALL,
    NODE_GROUP,
    NODE_USER,
    build_users_filter,
    users_filter_all,
    users_filter_for_group,
    users_filter_for_user,
)


def test_root_filter() -> None:
    assert users_filter_all() == [{"NodeType": NODE_ALL, "UserID": NODE_ALL}]


def test_group_is_node_type_14() -> None:
    assert users_filter_for_group(10) == [{"NodeType": NODE_GROUP, "UserID": 10}]
    assert NODE_GROUP == 14


def test_user_is_node_type_1() -> None:
    assert users_filter_for_user(4) == [{"NodeType": NODE_USER, "UserID": 4}]
    assert NODE_USER == 1


def test_build_combines_group_and_user() -> None:
    nodes = build_users_filter(group_id=10, user_id=4)
    assert {"NodeType": 14, "UserID": 10} in nodes
    assert {"NodeType": 1, "UserID": 4} in nodes


def test_build_neither_is_root() -> None:
    assert build_users_filter() == users_filter_all()


def test_compact_strips_blob_and_caps_list() -> None:
    data = {
        "TotalRecords": 50,
        "List": [
            {"AliasID": i, "Thumbnail": "AAAA" * 100, "Text": "x" * 1000}
            for i in range(20)
        ],
    }
    out = compact_api_payload(data, list_cap=5, text_max=50)
    assert out["_truncated"] is True
    assert len(out["List"]) == 5
    assert out["List"][0]["Thumbnail"] == "[omitted binary/blob]"
    assert out["List"][0]["Text"].endswith("(+950)") or "…" in out["List"][0]["Text"]
