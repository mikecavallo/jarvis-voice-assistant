"""Tests for config.Config: defaults, env overrides, file permissions."""

import json
import logging
import stat

import pytest

from config import Config


@pytest.fixture
def in_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_creates_default_config_without_secrets(in_tmp):
    cfg = Config()
    path = in_tmp / "config.json"
    data = json.loads(path.read_text())
    assert data["general"]["wake_word"] == "jarvis"
    assert data["elevenlabs"]["api_key"] == ""
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert cfg.get("speech_recognition", "engine") == "whisper"


def test_env_var_overrides_file(in_tmp, monkeypatch):
    cfg = Config()
    monkeypatch.setenv("SPEECH_RECOGNITION_ENGINE", "remote")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el-test-key")
    assert cfg.get("speech_recognition", "engine") == "remote"
    assert cfg.get("elevenlabs", "api_key") == "el-test-key"


def test_missing_key_returns_default(in_tmp):
    cfg = Config()
    assert cfg.get("nope", "missing", "fallback") == "fallback"


def test_loads_existing_file(in_tmp):
    (in_tmp / "config.json").write_text(json.dumps({"general": {"wake_word": "friday"}}))
    assert Config().get("general", "wake_word") == "friday"


def test_invalid_json_falls_back_to_defaults(in_tmp):
    (in_tmp / "config.json").write_text("{not json")
    cfg = Config()
    assert cfg.get("general", "wake_word") == "jarvis"


def test_set_persists_and_warns_on_secrets(in_tmp, caplog):
    cfg = Config()
    with caplog.at_level(logging.WARNING):
        cfg.set("elevenlabs", "api_key", "sk-this-looks-like-a-real-key")
    assert "sensitive" in caplog.text
    reloaded = json.loads((in_tmp / "config.json").read_text())
    assert reloaded["elevenlabs"]["api_key"] == "sk-this-looks-like-a-real-key"


def test_get_api_key_reads_environment_only(in_tmp, monkeypatch):
    cfg = Config()
    assert cfg.get_api_key("openweather") is None
    monkeypatch.setenv("OPENWEATHER_API_KEY", "ow-key")
    assert cfg.get_api_key("openweather") == "ow-key"
