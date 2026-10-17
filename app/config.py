"""Central config. One switch — MODE — decides mock vs real Sarvam.

Nothing else in the app reads env vars directly; they all import from here.
Today (no keys): MODE defaults to "mock" and the whole app runs offline.
At the event: put your key in .env and set MODE=sarvam. That's the only change.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass  # dotenv is optional; env vars still work without it

# "mock" = runs offline with canned Vision results (rehearsal / no keys).
# "sarvam" = calls the real Sarvam APIs (needs SARVAM_API_KEY).
MODE = os.getenv("MODE", "mock").strip().lower()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
BASE_URL = os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai").strip()

# Model ids — verified against docs.sarvam.ai (2026-10-17). Override in .env if rejected.
CHAT_MODEL = os.getenv("SARVAM_CHAT_MODEL", "sarvam-105b-conversations")
TTS_MODEL = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3")
STT_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v4")

# Where spoken audio comes from. "browser" = Web Speech API (free, works today).
# "bulbul" = Sarvam TTS (nicer Telugu; only in MODE=sarvam). Default stays browser for reliability.
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "browser").strip().lower()

DATA_DIR = Path(__file__).resolve().parent / "data"


def is_mock() -> bool:
    return MODE != "sarvam" or not SARVAM_API_KEY
