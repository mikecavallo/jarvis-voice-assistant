"""
Client for a remote faster-whisper server (github.com/mikecavallo/jarvis-gpu-transcription).

Offloads speech-to-text to a GPU machine on the network instead of running
Whisper on the CPU of the machine Jarvis runs on.

Server contract (POST /transcribe/fast or /transcribe/accurate):
    multipart/form-data with
        audio_file  the WAV bytes (file part)
        language    form field, e.g. "en" ("auto" lets Whisper detect it)
    optional header X-API-Key when the server sets TRANSCRIPTION_API_KEY
    JSON response containing at least {"text": "..."}

Enable it with:
    SPEECH_RECOGNITION_ENGINE=remote
    SPEECH_RECOGNITION_REMOTE_URL=http://<gpu-host>:8000
    TRANSCRIPTION_API_KEY=<same key as the server>   (optional)
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

VALID_MODES = ("fast", "accurate")


class RemoteTranscriptionError(RuntimeError):
    """Raised when the remote transcription server cannot be used."""


def normalize_language(language: Optional[str]) -> str:
    """Convert a locale such as "en-US" to the bare Whisper code "en"."""
    if not language:
        return "auto"
    return language.split("-")[0].split("_")[0].lower()


class RemoteTranscriber:
    """Sends recorded audio to a jarvis-gpu-transcription server."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        mode: str = "fast",
        timeout: float = 30.0,
        session: Optional[requests.Session] = None,
    ):
        if not base_url:
            raise ValueError("base_url is required for remote transcription")
        if mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {VALID_MODES}, got {mode!r}")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or None
        self.mode = mode
        self.timeout = timeout
        self.session = session or requests.Session()

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/transcribe/{self.mode}"

    def transcribe(self, wav_bytes: bytes, language: Optional[str] = "en") -> Optional[str]:
        """
        Transcribe WAV audio on the remote server.

        Returns the stripped transcript, or None when the server heard nothing.
        Raises RemoteTranscriptionError on network, auth or server errors.
        """
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        files = {"audio_file": ("audio.wav", wav_bytes, "audio/wav")}
        data = {"language": normalize_language(language)}

        try:
            response = self.session.post(
                self.endpoint, files=files, data=data, headers=headers, timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise RemoteTranscriptionError(f"Could not reach {self.endpoint}: {exc}") from exc

        if response.status_code == 401:
            raise RemoteTranscriptionError("Remote transcription rejected the X-API-Key header (401)")
        if response.status_code != 200:
            raise RemoteTranscriptionError(
                f"Remote transcription failed with HTTP {response.status_code}: {response.text[:200]}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise RemoteTranscriptionError("Remote transcription returned invalid JSON") from exc

        text = (payload.get("text") or "").strip()
        logger.debug("Remote transcription (%s): %r", self.mode, text)
        return text or None

    def health(self) -> bool:
        """Return True when the server's /health endpoint answers 200."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False


def from_config(config) -> Optional[RemoteTranscriber]:
    """Build a RemoteTranscriber from Jarvis config/env, or None if no URL is set."""
    url = config.get("speech_recognition", "remote_url")
    if not url:
        return None
    mode = config.get("speech_recognition", "remote_mode", "fast") or "fast"
    timeout = float(config.get("speech_recognition", "remote_timeout", 30) or 30)
    return RemoteTranscriber(
        base_url=url,
        api_key=os.getenv("TRANSCRIPTION_API_KEY"),
        mode=mode,
        timeout=timeout,
    )
