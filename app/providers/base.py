"""The provider interface — the single seam between our app and Sarvam.

Everything model-shaped lives behind these five methods. The rest of the app
only ever calls a Provider; it never imports the Sarvam SDK directly. That is
why swapping mock -> real Sarvam is a one-file change (providers/sarvam.py) and
a one-line .env switch (MODE=sarvam).

Maps 1:1 to Sarvam's APIs:
    read_document / read_strip  -> Sarvam Vision (Document AI)
    assist_extract              -> Sarvam-105B (chat, JSON mode)  [the "agent" step]
    speak                       -> Bulbul (text-to-speech)
    transcribe                  -> Saaras (speech-to-text)
"""
from __future__ import annotations

from typing import List, Optional, Protocol


class Provider(Protocol):
    name: str

    def read_document(self, data: bytes, filename: str,
                      content_type: str = "handwritten",
                      language: str = "en-IN") -> str:
        """OCR a prescription image/PDF -> raw text. (Sarvam Vision)"""
        ...

    def read_strip(self, data: bytes, filename: str,
                   language: str = "en-IN", scenario: str = "match") -> dict:
        """Read a medicine strip -> {name, strength, expiry}. (Sarvam Vision)
        'scenario' is only used by the mock to pick a canned strip."""
        ...

    def assist_extract(self, raw_text: str) -> Optional[List[dict]]:
        """Optionally structure raw OCR into [{name, strength, dose, raw}].
        Returns None to let the deterministic parser handle it. (Sarvam-105B)"""
        ...

    def answer(self, question: str, context: str, language: str = "en-IN") -> str:
        """Answer a voice question grounded in the prescription. (Sarvam-105B)"""
        ...

    def speak(self, text: str, language: str = "en-IN") -> Optional[bytes]:
        """Return audio bytes, or None to let the browser speak. (Bulbul)"""
        ...

    def transcribe(self, audio: bytes, language: str = "en-IN") -> str:
        """Audio -> text. (Saaras)"""
        ...
