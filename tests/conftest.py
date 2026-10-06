"""
Shared pytest setup.

Several Jarvis modules create singletons at import time that write files to
the current directory (config.json, jarvis_state.json, memory/, credentials/).
Before anything is imported we move into a throwaway directory and clear API
keys so tests never touch real user data or call paid APIs.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

_WORKDIR = tempfile.mkdtemp(prefix="jarvis-tests-")
os.chdir(_WORKDIR)

for _var in (
    "OPENAI_API_KEY",
    "ELEVENLABS_API_KEY",
    "OPENWEATHER_API_KEY",
    "SERPAPI_KEY",
    "NEWS_API_KEY",
    "MCP_API_KEY",
    "TRANSCRIPTION_API_KEY",
    "SPEECH_RECOGNITION_ENGINE",
    "SPEECH_RECOGNITION_REMOTE_URL",
    "SYSTEM_COMMANDS_ENABLED",
):
    os.environ.pop(_var, None)
os.environ["ANONYMIZED_TELEMETRY"] = "False"


class FakeResponse:
    """Minimal stand-in for an aiohttp response used as an async context manager."""

    def __init__(self, status=200, payload=None):
        self.status = status
        self._payload = payload if payload is not None else {}

    async def json(self):
        return self._payload

    async def text(self):
        return str(self._payload)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    """Records requests and replays canned responses keyed by URL suffix."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []
        self.closed = False

    async def close(self):
        self.closed = True

    def _respond(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        for suffix, response in self.routes.items():
            if url.endswith(suffix):
                if isinstance(response, Exception):
                    raise response
                return response
        return FakeResponse(404, {"error": "no route"})

    def get(self, url, **kwargs):
        return self._respond("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self._respond("POST", url, **kwargs)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def fake_http(monkeypatch):
    """Patch aiohttp.ClientSession; call the fixture with {url_suffix: FakeResponse}."""
    import aiohttp

    sessions = []

    def install(routes):
        def factory(*args, **kwargs):
            session = FakeSession(routes)
            sessions.append(session)
            return session

        monkeypatch.setattr(aiohttp, "ClientSession", factory)
        return sessions

    return install
