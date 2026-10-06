"""Tests for the FastAPI MCP server: auth, validation, routing. No real APIs are called."""

import pytest
from fastapi.testclient import TestClient

from mcp_server import server
from mcp_server.security import InputValidator, RateLimiter

KEY = "test-mcp-key"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", KEY)
    monkeypatch.setattr(server, "rate_limiter", RateLimiter(max_requests=1000))
    return TestClient(server.app)


def auth(key=KEY):
    return {"Authorization": f"Bearer {key}"}


def test_health_is_public_and_reports_tools(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert set(body["tools"]) >= {"weather", "crypto", "search", "news", "filesystem", "system", "gmail"}
    assert body["tools"]["crypto"] is True
    assert body["status"] == "degraded"  # no API keys configured in tests
    assert response.headers["X-Frame-Options"] == "DENY"


def test_mcp_requires_bearer_token(client):
    payload = {"tool": "crypto", "action": "price", "parameters": {"symbol": "BTC"}}
    assert client.post("/mcp", json=payload).status_code in (401, 403)
    assert client.post("/mcp", json=payload, headers=auth("wrong")).status_code == 401


def test_missing_server_key_is_a_server_error(client, monkeypatch):
    monkeypatch.delenv("MCP_API_KEY")
    response = client.get("/crypto", params={"symbol": "BTC"}, headers=auth())
    assert response.status_code == 500


def test_mcp_dispatches_to_tool(client, monkeypatch):
    calls = []

    async def fake_execute(action, parameters):
        calls.append((action, parameters))
        return {"price": 1.0}

    monkeypatch.setattr(server.tools["crypto"], "execute", fake_execute)
    response = client.post(
        "/mcp",
        json={"tool": "crypto", "action": "price", "parameters": {"symbol": "BTC"}},
        headers=auth(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True and body["data"] == {"price": 1.0}
    assert calls == [("price", {"symbol": "BTC", "vs_currency": "usd"})]


def test_mcp_unknown_tool_and_bad_params(client):
    unknown = client.post("/mcp", json={"tool": "teleport", "action": "go"}, headers=auth())
    assert unknown.status_code == 400
    bad = client.post(
        "/mcp", json={"tool": "crypto", "action": "price", "parameters": {"symbol": "$(rm)"}}, headers=auth()
    )
    assert bad.status_code == 400


def test_weather_endpoint_maps_forecast_flag(client, monkeypatch):
    calls = []

    async def fake_execute(action, parameters):
        calls.append((action, parameters))
        return {"ok": True}

    monkeypatch.setattr(server.tools["weather"], "execute", fake_execute)
    assert client.get("/weather", params={"location": "Leland, NC", "forecast": "true"}, headers=auth()).json() == {
        "ok": True
    }
    assert calls == [("forecast", {"location": "Leland, NC"})]


def test_rate_limit_returns_429(monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", KEY)
    monkeypatch.setattr(server, "rate_limiter", RateLimiter(max_requests=1))
    limited = TestClient(server.app)
    assert limited.get("/crypto", params={"symbol": "BTC", "vs_currency": "USD"}, headers=auth()).status_code != 429
    assert limited.get("/crypto", params={"symbol": "BTC"}, headers=auth()).status_code == 429


def test_input_validator_blocks_injection():
    with pytest.raises(ValueError):
        InputValidator.sanitize_string("paris; rm -rf /")
    assert InputValidator.sanitize_string("  Leland  ") == "Leland"
    assert InputValidator.validate_email("a@b.co")
    assert not InputValidator.validate_email("not-an-email")
