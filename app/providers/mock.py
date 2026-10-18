"""Mock provider: runs the entire app offline, with no API keys.

read_document returns a realistic handwritten-style prescription; read_strip
returns one of four canned strips so the presenter can show each verdict
(match / not-on-list / expired / unreadable). assist_extract returns None so the
deterministic parser does the structuring. speak returns None so the browser's
built-in voice speaks.
"""
from __future__ import annotations

from typing import List, Optional

from app import config

_MOCK_RX = (config.DATA_DIR / "mock_prescription.txt")

# Canned strips keyed by the scenario the UI asks for.
_STRIPS = {
    "match":      {"name": "Dolo 650",      "strength": "650 mg", "expiry": "03/2027"},
    "not_on_list":{"name": "Shelcal 500",   "strength": "500 mg", "expiry": "12/2027"},
    "expired":    {"name": "Azithral 500",  "strength": "500 mg", "expiry": "06/2026"},
    "unreadable": {"name": "",              "strength": "",       "expiry": ""},
}


class MockProvider:
    name = "mock"

    def read_document(self, data: bytes, filename: str,
                      content_type: str = "handwritten",
                      language: str = "en-IN") -> str:
        if _MOCK_RX.exists():
            return _MOCK_RX.read_text(encoding="utf-8")
        return ("Rx\nTab. Dolo 650 1-0-1 x5d a/f\n"
                "Tab. Pan-D 40 1-0-0 x5d b/f\nCap. Azithral 500 0-0-1 x3d\n"
                "Tab. Metformin 500 1-0-1 x30d a/f")

    def read_strip(self, data: bytes, filename: str,
                   language: str = "en-IN", scenario: str = "match") -> dict:
        return dict(_STRIPS.get(scenario, _STRIPS["match"]))

    def assist_extract(self, raw_text: str) -> Optional[List[dict]]:
        return None  # let the deterministic parser do it

    def answer(self, question: str, context: str, language: str = "en-IN") -> str:
        q = (question or "").lower()
        # small rule-based stand-in; in live mode Sarvam-105B answers
        if "night" in q or "రాత్రి" in question or "रात" in question:
            return "Dolo 650 and Metformin 500 are taken at night."
        if "how many" in q or "days" in q:
            return "Dolo 650 for 5 days, Azithral 500 for 3 days, Metformin 500 for 30 days."
        return "Please ask about a specific time of day, like morning or night."

    def speak(self, text: str, language: str = "en-IN") -> Optional[bytes]:
        return None  # browser speaks

    def transcribe(self, audio: bytes, language: str = "en-IN") -> str:
        return "[typed-input fallback]"  # browser does STT in mock mode
