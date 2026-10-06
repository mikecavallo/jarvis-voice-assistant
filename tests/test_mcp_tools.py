"""Tests for MCP tool handlers. External HTTP is replaced by tests/conftest.FakeSession."""

import asyncio

import pytest

from conftest import FakeResponse
from mcp_server.tools.crypto import CryptoTool
from mcp_server.tools.filesystem import FilesystemTool
from mcp_server.tools.news import NewsTool
from mcp_server.tools.search import SearchTool
from mcp_server.tools.system import SystemTool
from mcp_server.tools.weather import WeatherTool


def run(coro):
    return asyncio.run(coro)


# --- weather ---------------------------------------------------------------

def test_weather_without_key_reports_not_configured():
    tool = WeatherTool()
    assert tool.health_check() is False
    assert run(tool.execute("current", {"location": "Wilmington"})) == {
        "error": "OpenWeatherMap API key not configured"
    }


def test_weather_current_parses_response(monkeypatch, fake_http):
    monkeypatch.setenv("OPENWEATHER_API_KEY", "ow-test")
    payload = {
        "name": "Wilmington",
        "sys": {"country": "US"},
        "main": {"temp": 24.5, "humidity": 70, "pressure": 1012},
        "weather": [{"description": "clear sky"}],
        "wind": {"speed": 3.1},
    }
    sessions = fake_http({"/weather": FakeResponse(200, payload)})
    result = run(WeatherTool().execute("current", {"location": "Wilmington", "units": "imperial"}))

    assert result == {
        "location": "Wilmington",
        "country": "US",
        "temperature": 24.5,
        "description": "clear sky",
        "humidity": 70,
        "pressure": 1012,
        "wind_speed": 3.1,
        "units": "imperial",
    }
    call = sessions[0].calls[0]
    assert call["params"] == {"q": "Wilmington", "appid": "ow-test", "units": "imperial"}


def test_weather_forecast_and_api_error(monkeypatch, fake_http):
    monkeypatch.setenv("OPENWEATHER_API_KEY", "ow-test")
    forecast = {
        "city": {"name": "Leland", "country": "US"},
        "list": [
            {"dt_txt": "2026-10-06 12:00:00", "main": {"temp": 20, "humidity": 50}, "weather": [{"description": "rain"}]}
        ],
    }
    fake_http({"/forecast": FakeResponse(200, forecast), "/weather": FakeResponse(401, {})})
    tool = WeatherTool()
    result = run(tool.execute("forecast", {"location": "Leland"}))
    assert result["location"] == "Leland"
    assert result["forecast"][0]["description"] == "rain"
    assert result["forecast"][0]["wind_speed"] is None

    assert run(tool.execute("current", {"location": "Leland"})) == {"error": "Weather API error: 401"}
    assert "Unknown weather action" in run(tool.execute("radar", {}))["error"]


def test_weather_network_failure_is_caught(monkeypatch, fake_http):
    monkeypatch.setenv("OPENWEATHER_API_KEY", "ow-test")
    fake_http({"/weather": OSError("network down")})
    result = run(WeatherTool().execute("current", {"location": "X"}))
    assert result["error"].startswith("Weather request failed")


# --- crypto ----------------------------------------------------------------

def test_crypto_price(fake_http):
    payload = {"bitcoin": {"usd": 100.0, "usd_market_cap": 5.0, "usd_24h_vol": 2.0, "usd_24h_change": -1.5}}
    sessions = fake_http({"/simple/price": FakeResponse(200, payload)})
    result = run(CryptoTool().execute("price", {"symbol": "BITCOIN"}))
    assert result == {
        "symbol": "bitcoin",
        "price": 100.0,
        "currency": "usd",
        "market_cap": 5.0,
        "volume_24h": 2.0,
        "change_24h": -1.5,
    }
    assert sessions[0].calls[0]["params"]["ids"] == "bitcoin"


def test_crypto_unknown_coin_and_trending(fake_http):
    trending = {"coins": [{"item": {"name": "Solana", "symbol": "SOL", "market_cap_rank": 5, "thumb": "t"}}]}
    fake_http({"/simple/price": FakeResponse(200, {}), "/search/trending": FakeResponse(200, trending)})
    tool = CryptoTool()
    assert run(tool.execute("price", {"symbol": "notacoin"})) == {"error": "Cryptocurrency 'notacoin' not found"}
    assert run(tool.execute("trending", {}))["trending_coins"][0]["symbol"] == "SOL"


# --- news and search -------------------------------------------------------

def test_news_headlines(monkeypatch, fake_http):
    monkeypatch.setenv("NEWS_API_KEY", "news-test")
    payload = {
        "totalResults": 1,
        "articles": [{"title": "T", "description": "D", "url": "u", "source": {"name": "S"}, "publishedAt": "p"}],
    }
    sessions = fake_http({"/top-headlines": FakeResponse(200, payload)})
    result = run(NewsTool().execute("headlines", {"category": "technology"}))
    assert result == {
        "articles": [{"title": "T", "description": "D", "url": "u", "source": "S", "published_at": "p"}],
        "total_results": 1,
    }
    assert sessions[0].calls[0]["params"]["category"] == "technology"


def test_news_and_search_without_keys():
    assert run(NewsTool().execute("headlines", {})) == {"error": "NewsAPI key not configured"}
    assert run(SearchTool().execute("search", {"query": "x"})) == {"error": "SerpAPI key not configured"}


def test_search_results(monkeypatch, fake_http):
    monkeypatch.setenv("SERPAPI_KEY", "serp-test")
    payload = {"organic_results": [{"title": "Python", "link": "https://python.org", "snippet": "s", "extra": 1}]}
    fake_http({"serpapi.com/search": FakeResponse(200, payload)})
    result = run(SearchTool().execute("search", {"query": "python"}))
    assert result == {"results": [{"title": "Python", "link": "https://python.org", "snippet": "s"}], "query": "python"}


# --- filesystem ------------------------------------------------------------

@pytest.fixture
def fs_tool(tmp_path):
    root = tmp_path / "home" / "al"
    root.mkdir(parents=True)
    tool = FilesystemTool()
    tool.safe_root = root
    return tool


def test_filesystem_write_read_list(fs_tool):
    assert run(fs_tool.execute("write", {"path": "notes/todo.txt", "content": "buy milk"}))["success"] is True
    assert run(fs_tool.execute("read", {"path": "notes/todo.txt"}))["content"] == "buy milk"
    listing = run(fs_tool.execute("list", {"path": "notes"}))
    assert listing["items"] == [{"name": "todo.txt", "type": "file", "size": 8}]
    assert "File not found" in run(fs_tool.execute("read", {"path": "missing.txt"}))["error"]


@pytest.mark.parametrize("path", ["../outside.txt", "/etc/passwd", "../alice/secret.txt"])
def test_filesystem_blocks_paths_outside_root(fs_tool, path):
    sibling = fs_tool.safe_root.parent / "alice"
    sibling.mkdir(exist_ok=True)
    (sibling / "secret.txt").write_text("nope")
    result = run(fs_tool.execute("read", {"path": path}))
    assert "outside safe root" in result["error"]


# --- system ----------------------------------------------------------------

def test_system_commands_disabled_by_default():
    tool = SystemTool()
    assert tool.health_check() is False
    assert "disabled" in run(tool.execute("run", {"command": "test"}))["error"]


def test_system_whitelist(monkeypatch):
    monkeypatch.setenv("SYSTEM_COMMANDS_ENABLED", "true")
    tool = SystemTool()
    assert "not allowed" in run(tool.execute("run", {"command": "rm"}))["error"]
    result = run(tool.execute("run", {"command": "test"}))
    assert result["success"] is True
    assert result["stdout"].strip() == "System control test successful"
