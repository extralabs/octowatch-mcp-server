"""TreeviewUsers POST body builders.

Cloud Overall*/Monitoring/Dashboard POSTs expect List[TreeviewUsers] with:
  NodeType -666666 = all, 14 = group, 1 = user (AliasID).
Do NOT confuse with GetUsersGroups2 Item.Type (0=root, 1=group, 2=user).
"""

from __future__ import annotations

from octowatch_mcp.config import ROOT_FILTER

# _TypeNodeID (common)
NODE_ALL = -666666
NODE_USER = 1
NODE_GROUP = 14


def users_filter_all() -> list[dict[str, int]]:
    return list(ROOT_FILTER)


def users_filter_for_group(group_id: int) -> list[dict[str, int]]:
    """Filter by group (NodeType=14, UserID=group id)."""
    return [{"NodeType": NODE_GROUP, "UserID": group_id}]


def users_filter_for_user(alias_id: int) -> list[dict[str, int]]:
    """Filter by one employee (NodeType=1, UserID=AliasID)."""
    return [{"NodeType": NODE_USER, "UserID": alias_id}]


def build_users_filter(
    *,
    group_id: int | None = None,
    user_id: int | None = None,
) -> list[dict[str, int]]:
    """Compose filter nodes. Server GetWhere ORs groups and users.

    Neither set → all users (-666666).
    """
    nodes: list[dict[str, int]] = []
    if group_id is not None:
        nodes.append({"NodeType": NODE_GROUP, "UserID": group_id})
    if user_id is not None:
        nodes.append({"NodeType": NODE_USER, "UserID": user_id})
    return nodes if nodes else users_filter_all()
