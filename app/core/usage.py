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

# Approx INR rates observed on the Indus usage console (Vision = Doc Agents).
# These drive the on-screen estimate only; the Indus console is authoritative.
RATE_VISION_PER_PAGE = 0.50      # ₹ per page
RATE_CHAT_PER_1K = 0.025         # ₹ per 1,000 chat tokens


def _est_cost() -> float:
    pages = _tokens["vision_pages"] or _counts["vision"]   # 1 page/call if unknown
    cost = pages * RATE_VISION_PER_PAGE
    cost += (_tokens["chat_tokens"] / 1000.0) * RATE_CHAT_PER_1K
    return round(cost, 2)


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
        return {"total": total, "by_kind": dict(_counts),
                "est_cost_inr": _est_cost(), **_tokens}


def reset() -> None:
    with _lock:
        for k in _counts:
            _counts[k] = 0
        _tokens["chat_tokens"] = 0
        _tokens["vision_pages"] = 0
