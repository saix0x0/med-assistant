"""Tracks how many billable Sarvam calls this session has made.

Sarvam bills per API call (Vision jobs, chat completions, TTS, STT). There is no
"credits remaining" endpoint, so we count the calls we make — which is the number
that actually spends credits — and show it in the UI. Mock calls are free and are
not counted. Status-poll requests are not counted; only the billable start calls.
"""
from __future__ import annotations

from threading import Lock

_lock = Lock()
_counts = {"vision": 0, "chat": 0, "tts": 0, "stt": 0}
_tokens = {"chat_tokens": 0, "vision_pages": 0}


def add(kind: str, tokens: int = 0, pages: int = 0) -> None:
    with _lock:
        if kind in _counts:
            _counts[kind] += 1
        if tokens:
            _tokens["chat_tokens"] += tokens
        if pages:
            _tokens["vision_pages"] += pages


def snapshot() -> dict:
    with _lock:
        total = sum(_counts.values())
        return {"total": total, "by_kind": dict(_counts), **_tokens}


def reset() -> None:
    with _lock:
        for k in _counts:
            _counts[k] = 0
        _tokens["chat_tokens"] = 0
        _tokens["vision_pages"] = 0
