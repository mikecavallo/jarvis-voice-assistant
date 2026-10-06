"""Tests for keyword routing in the Jarvis-side MCP client."""

import pytest

from memory.mcp_client import MCPClient


@pytest.mark.parametrize(
    "text,tool",
    [
        ("What's the price of bitcoin?", "crypto"),
        ("Will it rain in Leland?", "weather"),
        ("Give me the latest headlines", "news"),
        ("search for the best pizza", "search"),
        ("list files in my documents", "filesystem"),
        ("What's on my calendar tomorrow?", "calendar"),
        ("check my unread emails", "gmail"),
        ("Tell me a joke", None),
        ("Tell me something interesting", None),
    ],
)
def test_can_handle_request(text, tool):
    assert MCPClient().can_handle_request(text) == tool


def test_unknown_tool_raises():
    import asyncio

    with pytest.raises(ValueError):
        asyncio.run(MCPClient().call_tool("teleport"))
