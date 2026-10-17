"""Dosing parser. Pure, deterministic, no AI.

Turns the shorthand a doctor writes ("1-0-1", "BD", "TDS a/f x5d") into a
structured schedule we can speak in plain language. This runs in every mode and
in both mock and real-Sarvam runs, so it is the piece that guarantees we never
mis-state a schedule even when the OCR text is messy.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Dose:
    morning: int = 0
    noon: int = 0
    evening: int = 0
    night: int = 0
    prn: bool = False            # "as needed" (SOS)
    stat: bool = False           # once, immediately
    food: Optional[str] = None   # "before" | "after" | None
    days: Optional[int] = None
    raw: str = ""

    @property
    def total_per_day(self) -> int:
        return self.morning + self.noon + self.evening + self.night

    @property
    def times(self) -> list:
        out = []
        if self.morning:
            out.append("morning")
        if self.noon:
            out.append("noon")
        if self.evening:
            out.append("evening")
        if self.night:
            out.append("night")
        return out


# Standard abbreviations -> slot pattern (morning, noon, evening, night)
_ABBREV = {
    "OD": (1, 0, 0, 0),   # once daily
    "QD": (1, 0, 0, 0),
    "BD": (1, 0, 0, 1),   # twice daily
    "BID": (1, 0, 0, 1),
    "TDS": (1, 1, 0, 1),  # thrice daily
    "TID": (1, 1, 0, 1),
    "QID": (1, 1, 1, 1),  # four times
    "QDS": (1, 1, 1, 1),
    "HS": (0, 0, 0, 1),   # at bedtime
    "ON": (0, 0, 0, 1),   # at night
    "MANE": (1, 0, 0, 0), # in the morning
}

_FOOD_AFTER = ("a/f", "af", "p/c", "pc", "after food", "after meal", "post food")
_FOOD_BEFORE = ("b/f", "bf", "a/c", "ac", "before food", "before meal", "empty stomach")

_DAYS_PATTERNS = [
    re.compile(r"x\s*(\d{1,3})\s*d", re.I),          # x5d, x 5 d
    re.compile(r"for\s*(\d{1,3})\s*days?", re.I),    # for 5 days
    re.compile(r"\b(\d{1,2})\s*/\s*7\b"),            # 5/7  (n days per week-ish shorthand)
]


def parse_dose(text: str) -> Dose:
    """Parse a dosing fragment such as '1-0-1 a/f x5d' or 'BD after food'."""
    raw = text or ""
    t = " " + raw.lower() + " "
    dose = Dose(raw=raw.strip())

    # as-needed / stat
    if re.search(r"\bsos\b|\bprn\b|as\s*needed|if\s*required", t):
        dose.prn = True
    if re.search(r"\bstat\b|immediately", t):
        dose.stat = True

    # food timing
    if any(k in t for k in _FOOD_AFTER):
        dose.food = "after"
    elif any(k in t for k in _FOOD_BEFORE):
        dose.food = "before"

    # duration
    for pat in _DAYS_PATTERNS:
        m = pat.search(raw)
        if m:
            dose.days = int(m.group(1))
            break

    # numeric slot pattern: 1-0-1, 1-1-1, 1-0-0-1, 0-0-1, with OCR-friendly separators
    slot = re.search(r"\b([01½\d])\s*[-–xX|/]\s*([01½\d])\s*[-–xX|/]\s*([01½\d])(?:\s*[-–xX|/]\s*([01½\d]))?\b", raw)
    if slot:
        vals = [slot.group(i) for i in range(1, 5)]
        nums = [_num(v) for v in vals if v is not None]
        if len(nums) == 3:
            dose.morning, dose.noon, dose.night = nums
        elif len(nums) == 4:
            dose.morning, dose.noon, dose.evening, dose.night = nums
        return dose

    # word abbreviation (BD / TDS / OD ...)
    for abbr, pat in _ABBREV.items():
        if re.search(r"\b" + abbr + r"\b", raw, re.I):
            dose.morning, dose.noon, dose.evening, dose.night = pat
            return dose

    return dose


def _num(v: str) -> int:
    if v == "½":
        return 1  # treat half as a dose present; we speak "half" separately if needed
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0
