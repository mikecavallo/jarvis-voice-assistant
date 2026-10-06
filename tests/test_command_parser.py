"""Tests for the regex command parser (no audio, browser or LLM involved)."""

import re

import pytest

import command_parser as cp_module
from command_parser import CommandParser
from memory.state_manager import JarvisState


@pytest.fixture
def state(tmp_path, monkeypatch):
    fresh = JarvisState(str(tmp_path / "state.json"))
    monkeypatch.setattr(cp_module, "jarvis_state", fresh)
    return fresh


@pytest.fixture
def opened(monkeypatch):
    urls = []
    monkeypatch.setattr(cp_module.webbrowser, "open", lambda url: urls.append(url) or True)
    return urls


@pytest.fixture
def parser(state, opened):
    return CommandParser()


def test_time_command(parser):
    response = parser.parse_command("Hey, what time is it?")
    assert re.match(r"The current time is \d{2}:\d{2} (AM|PM)$", response)


def test_date_command(parser):
    assert parser.parse_command("what's today's date").startswith("Today is ")


def test_search_google_url_encodes_query(parser, opened):
    response = parser.parse_command("search google for python tutorials & tips")
    assert response == "Searching Google for python tutorials & tips"
    assert opened == ["https://www.google.com/search?q=python+tutorials+%26+tips"]


def test_open_website_adds_https(parser, opened):
    assert parser.parse_command("go to example.com") == "Opening https://example.com"
    assert opened == ["https://example.com"]


def test_open_browser(parser, opened):
    assert parser.parse_command("open browser") == "Opening your web browser"
    assert opened == ["https://www.google.com"]


def test_help_lists_every_command(parser):
    response = parser.parse_command("help")
    for name in parser.list_commands():
        assert name in response


def test_goals_and_todos_come_from_state(parser, state):
    assert "Build a modular voice-controlled AI assistant" in parser.parse_command("show goals")
    assert parser.parse_command("show tasks") == "No pending tasks"
    state.add_todo("Write tests", "claude", "high")
    assert parser.parse_command("show tasks") == "Pending tasks: Write tests assigned to claude"


def test_quit_response_triggers_shutdown_phrase(parser):
    # main.py shuts down when the response contains "shutting down"
    assert "shutting down" in parser.parse_command("goodbye").lower()


def test_empty_input(parser):
    assert parser.parse_command("") == "I didn't catch that. Could you repeat?"


def test_unmatched_input_falls_back_to_conversation(parser, monkeypatch):
    seen = []

    async def fake_response(text):
        seen.append(text)
        return "LLM says hi"

    monkeypatch.setattr(cp_module.conversation_manager, "get_response", fake_response)
    assert parser.parse_command("Tell me a joke") == "LLM says hi"
    assert seen == ["tell me a joke"]


def test_conversation_failure_returns_helpful_message(parser, monkeypatch):
    async def broken(text):
        raise RuntimeError("no provider")

    monkeypatch.setattr(cp_module.conversation_manager, "get_response", broken)
    response = parser.parse_command("tell me a joke")
    assert "Say 'help'" in response


def test_command_errors_are_reported_not_raised(parser):
    def explode():
        raise ValueError("boom")

    parser.add_custom_command("explode", [r"self destruct"], explode, "Raise an error")
    assert parser.parse_command("self destruct") == "Sorry, I encountered an error: boom"


def test_custom_command_with_capture_group(parser):
    parser.add_custom_command("echo", [r"repeat after me (.+)"], lambda text: text.upper(), "Echo")
    assert parser.parse_command("repeat after me hello") == "HELLO"
    assert parser.get_command_patterns("echo") == [r"repeat after me (.+)"]
    assert parser.remove_command("echo") is True
    assert parser.remove_command("echo") is False
    assert parser.get_command_patterns("echo") is None
