"""Tests for the jarvis-gpu-transcription client (HTTP is faked)."""

import pytest
import requests

from remote_transcription import (
    RemoteTranscriber,
    RemoteTranscriptionError,
    from_config,
    normalize_language,
)


class FakeHTTPResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeRequestsSession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


def test_sends_multipart_audio_and_language_form_field():
    session = FakeRequestsSession(FakeHTTPResponse(200, {"text": "  turn on the lights "}))
    client = RemoteTranscriber("http://gpu-box:8000/", api_key="secret", session=session)

    assert client.transcribe(b"RIFFdata", language="en-US") == "turn on the lights"

    url, kwargs = session.calls[0]
    assert url == "http://gpu-box:8000/transcribe/fast"
    assert kwargs["files"]["audio_file"][1] == b"RIFFdata"
    assert kwargs["data"] == {"language": "en"}
    assert kwargs["headers"] == {"X-API-Key": "secret"}
    # model/language must not travel as query parameters
    assert "params" not in kwargs


def test_no_api_key_sends_no_header_and_accurate_mode():
    session = FakeRequestsSession(FakeHTTPResponse(200, {"text": "hi"}))
    client = RemoteTranscriber("http://gpu-box:8000", mode="accurate", session=session)
    client.transcribe(b"x")
    url, kwargs = session.calls[0]
    assert url.endswith("/transcribe/accurate")
    assert kwargs["headers"] == {}


def test_empty_transcript_is_none():
    session = FakeRequestsSession(FakeHTTPResponse(200, {"text": "   "}))
    assert RemoteTranscriber("http://h", session=session).transcribe(b"x") is None


@pytest.mark.parametrize(
    "response,message",
    [
        (FakeHTTPResponse(401, {"detail": "bad key"}), "401"),
        (FakeHTTPResponse(500, None, text="model crashed"), "HTTP 500"),
        (FakeHTTPResponse(200, None), "invalid JSON"),
    ],
)
def test_server_errors_raise(response, message):
    client = RemoteTranscriber("http://h", session=FakeRequestsSession(response))
    with pytest.raises(RemoteTranscriptionError, match=message):
        client.transcribe(b"x")


def test_network_error_raises():
    session = FakeRequestsSession(error=requests.ConnectionError("refused"))
    client = RemoteTranscriber("http://h", session=session)
    with pytest.raises(RemoteTranscriptionError, match="Could not reach"):
        client.transcribe(b"x")
    assert client.health() is False


def test_health_ok():
    session = FakeRequestsSession(FakeHTTPResponse(200, {"status": "healthy"}))
    assert RemoteTranscriber("http://h", session=session).health() is True


def test_invalid_arguments():
    with pytest.raises(ValueError):
        RemoteTranscriber("")
    with pytest.raises(ValueError):
        RemoteTranscriber("http://h", mode="turbo")


@pytest.mark.parametrize(
    "value,expected", [("en-US", "en"), ("pt_BR", "pt"), ("EN", "en"), (None, "auto"), ("", "auto")]
)
def test_normalize_language(value, expected):
    assert normalize_language(value) == expected


class StubConfig:
    def __init__(self, values):
        self.values = values

    def get(self, section, key, default=None):
        return self.values.get(key, default)


def test_from_config(monkeypatch):
    assert from_config(StubConfig({})) is None
    monkeypatch.setenv("TRANSCRIPTION_API_KEY", "k")
    client = from_config(StubConfig({"remote_url": "http://gpu:8000", "remote_mode": "accurate"}))
    assert client.endpoint == "http://gpu:8000/transcribe/accurate"
    assert client.api_key == "k"
