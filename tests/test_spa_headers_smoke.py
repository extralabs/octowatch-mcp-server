"""Live smoke: SPA-aligned GET headers (skipped if OCTOWATCH_SKIP_LIVE=1)."""

from __future__ import annotations

import os

import pytest

from octowatch_mcp.client import OctoWatchClient


@pytest.mark.skipif(os.getenv("OCTOWATCH_SKIP_LIVE") == "1", reason="live API skipped")
def test_spa_aligned_gets() -> None:
    with OctoWatchClient() as client:
        client.login()
        alias_id = 1

        # GetUserData2 is GET + AliasID (not POST TreeviewUsers)
        user_data = client.get_user_info("user_data", alias_id=alias_id)
        assert user_data is not None

        tooltip = client.get_user_info("tooltip", alias_id=alias_id)
        assert isinstance(tooltip, dict)

        # GetGroup = path for AliasID
        groups = client.get_user_info("group", alias_id=alias_id)
        assert groups is not None

        # GetDayStructure always sends ProductivityFilter + ActivityTypeFilter
        day = client.day_structure(user_id=alias_id, productivity_filter=0, activity_type_filter=0)
        assert isinstance(day, dict)

        # GetProfiles2 always sends ProfilesType + AliasID + AliasType
        profiles = client.get_account_readonly("profiles", profiles_type=0)
        assert profiles is not None

        # Stream: GET contracts
        which = client.stream_meta("which_content", alias_id=alias_id)
        assert which["WhichContentExists"] in (0, 1, 2)

        videos = client.stream_meta("videos", alias_id=alias_id)
        assert videos is not None

        downloads = client.stream_meta("downloads")
        assert downloads is not None
