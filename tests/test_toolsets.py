"""Unit tests for OCTOWATCH_TOOLSETS resolution."""

from __future__ import annotations

import pytest

from octowatch_mcp.toolsets import (
    ALL_TOOLS,
    CONSOLE_TOOLS,
    CORE_TOOLS,
    resolve_enabled_tools,
)


def test_all_default():
    assert resolve_enabled_tools("all") is None
    assert resolve_enabled_tools("") is None
    assert resolve_enabled_tools("  ALL  ") is None


def test_core_only():
    enabled = resolve_enabled_tools("core")
    assert enabled == CORE_TOOLS
    assert "list_monitoring" not in enabled


def test_console_auto_includes_core():
    enabled = resolve_enabled_tools("console")
    assert enabled == ALL_TOOLS
    assert CORE_TOOLS <= enabled
    assert CONSOLE_TOOLS <= enabled


def test_core_console_comma():
    assert resolve_enabled_tools("core,console") == ALL_TOOLS


def test_unknown_raises():
    with pytest.raises(ValueError, match="Unknown"):
        resolve_enabled_tools("billing")
