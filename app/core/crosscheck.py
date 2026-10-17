"""Cross-check a medicine strip against the saved prescription. No AI.

This is the part no existing tool does: given what a strip says (name, strength,
expiry) and the patient's prescription, decide one of four verdicts. It never
advises; it only reports what is written, and admits when it cannot read.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.core import medicines as med_mod
from app.core.prescription import Prescription

# Verdict codes (UI maps these to colour + icon; wording lives in safety.py)
ON_LIST = "on_list"
NOT_ON_LIST = "not_on_list"
EXPIRED = "expired"
UNREADABLE = "unreadable"

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


@dataclass
class StripResult:
    verdict: str
    read_name: str
    name: Optional[str]
    strength: Optional[str]
    expiry_text: Optional[str]
    expired: bool
    matched_medicine: Optional[dict]   # the prescription entry it lines up with
    confidence: float


def check(strip_name: str, strength: Optional[str], expiry_text: Optional[str],
          rx: Optional[Prescription], today: Optional[date] = None) -> StripResult:
    today = today or date.today()
    name = (strip_name or "").strip()

    # 1. Can we even read it?
    m = med_mod.match(name)
    if not name or not m.matched:
        return StripResult(UNREADABLE, name, None, strength, expiry_text,
                           False, None, m.score if name else 0.0)

    # 2. Expiry (reported regardless of list status; expired is the loudest verdict)
    expired = _is_expired(expiry_text, today)

    # 3. Is it on the prescription? (compare by ingredient first, then name)
    matched_entry = _find_in_rx(m, rx)

    if expired:
        return StripResult(EXPIRED, name, m.name, strength, expiry_text,
                           True, matched_entry, m.score)
    if matched_entry is None:
        return StripResult(NOT_ON_LIST, name, m.name, strength, expiry_text,
                           False, None, m.score)
    return StripResult(ON_LIST, name, m.name, strength, expiry_text,
                       False, matched_entry, m.score)


def _find_in_rx(m: med_mod.MedMatch, rx: Optional[Prescription]) -> Optional[dict]:
    if rx is None:
        return None
    for med in rx.medicines:
        if m.ingredient and med.ingredient and \
                _norm(m.ingredient) == _norm(med.ingredient):
            return med.to_dict()
        if m.name and med.name and _norm(m.name) == _norm(med.name):
            return med.to_dict()
    return None


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _is_expired(text: Optional[str], today: date) -> bool:
    if not text:
        return False
    t = text.lower()
    # MM/YYYY or MM/YY
    m = re.search(r"\b(\d{1,2})\s*[/-]\s*(\d{2,4})\b", t)
    if m:
        mon, yr = int(m.group(1)), int(m.group(2))
        if yr < 100:
            yr += 2000
        if 1 <= mon <= 12:
            return _end_of_month(yr, mon) < today
    # MMM YYYY  (e.g. "MAR 2027", "Mar-2027")
    m = re.search(r"\b([a-z]{3})\w*\s*[-/ ]?\s*(\d{4})\b", t)
    if m and m.group(1)[:3] in _MONTHS:
        mon, yr = _MONTHS[m.group(1)[:3]], int(m.group(2))
        return _end_of_month(yr, mon) < today
    return False


def _end_of_month(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    from datetime import timedelta
    return date(year, month + 1, 1) - timedelta(days=1)
