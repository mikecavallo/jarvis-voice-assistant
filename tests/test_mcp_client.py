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


def test_list_files_posts_to_fs_endpoint_with_auth(monkeypatch, fake_http):
    import asyncio

    from conftest import FakeResponse

    monkeypatch.setenv("MCP_API_KEY", "k")
    sessions = fake_http({"/fs/Documents": FakeResponse(200, {"items": []})})
    result = asyncio.run(MCPClient("http://mcp:8000").list_files("Documents"))
    assert result == {"success": True, "data": {"items": []}}
    call = sessions[-1].calls[0]
    assert call["method"] == "POST"
    assert call["json"] == {"action": "list", "parameters": {}}
    assert call["headers"] == {"Authorization": "Bearer k"}


def test_list_files_without_key(monkeypatch):
    import asyncio

    monkeypatch.delenv("MCP_API_KEY", raising=False)
    assert asyncio.run(MCPClient().list_files())["success"] is False
