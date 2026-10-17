"""Turn raw OCR text of a prescription into a structured, validated med list.

Flow:
  Vision gives raw text  ->  split into candidate medicine lines  ->  for each,
  pull the name + strength + dosing fragment  ->  dosing.parse_dose() and
  medicines.match().  The LLM (Sarvam-105B) can pre-structure the lines in real
  mode; whatever it returns is still validated here against the matcher, so a
  hallucinated drug name cannot survive.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.core import dosing as dosing_mod
from app.core import medicines as med_mod

# lines that start like a medicine order
_FORMS = r"(?:tab|tablet|cap|capsule|syp|syrup|inj|injection|susp|cream|oint|drop|drops|sachet)"
_LINE_HINT = re.compile(r"^\s*(?:rx|℞)?\s*(?:\d+[\).]\s*)?(?:" + _FORMS + r")\b", re.I)
_STRENGTH = re.compile(r"\b(\d{2,4}\s*(?:mg|ml|mcg|g|iu))\b", re.I)


@dataclass
class Medicine:
    raw_line: str
    read_name: str                 # what OCR/LLM produced
    name: Optional[str]            # validated canonical name (None if unmatched)
    ingredient: Optional[str]
    strength: Optional[str]
    dose: dosing_mod.Dose
    confidence: float
    matched: bool

    def to_dict(self) -> dict:
        d = self.dose
        return {
            "read_name": self.read_name,
            "name": self.name or self.read_name,
            "ingredient": self.ingredient,
            "strength": self.strength,
            "matched": self.matched,
            "confidence": self.confidence,
            "dose": {
                "morning": d.morning, "noon": d.noon,
                "evening": d.evening, "night": d.night,
                "prn": d.prn, "stat": d.stat,
                "food": d.food, "days": d.days,
                "total_per_day": d.total_per_day, "times": d.times,
                "code": d.raw,
            },
        }


@dataclass
class Prescription:
    raw_text: str = ""
    medicines: List[Medicine] = field(default_factory=list)
    unreadable: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "raw_text": self.raw_text,
            "medicines": [m.to_dict() for m in self.medicines],
            "unreadable": self.unreadable,
        }


def parse(raw_text: str, assisted: Optional[list] = None) -> Prescription:
    """assisted = optional list of {name, strength, dose} dicts from the LLM."""
    rx = Prescription(raw_text=raw_text or "")

    if assisted:
        for item in assisted:
            if not (item.get("name") or "").strip():
                continue                       # skip empty rows from the LLM
            rx.medicines.append(_build(
                raw_line=item.get("raw", ""),
                read_name=item.get("name", ""),
                strength=item.get("strength"),
                dose_text=item.get("dose", ""),
            ))
        _collect_unreadable(rx)
        return rx

    for line in (raw_text or "").splitlines():
        if not _LINE_HINT.search(line) and not _looks_like_med(line):
            continue
        name, strength, dose_text = _split_line(line)
        if not name:
            continue
        rx.medicines.append(_build(line, name, strength, dose_text))
    _collect_unreadable(rx)
    return rx


def _looks_like_med(line: str) -> bool:
    # a line with a strength (650 mg) and a dosing code is probably a med even
    # without a "Tab." prefix
    return bool(_STRENGTH.search(line) and re.search(r"[01][-–xX|/][01]", line))


def _split_line(line: str):
    s = re.sub(r"^\s*(?:rx|℞)?\s*(?:\d+[\).]\s*)?", "", line, flags=re.I).strip()
    s = re.sub(r"^\s*" + _FORMS + r"\.?\s*", "", s, flags=re.I).strip()
    strength_m = _STRENGTH.search(s)
    strength = strength_m.group(1) if strength_m else None
    # dosing fragment = everything from the first dose-ish token onward
    dose_start = re.search(r"([01½][-–xX|/][01½]|[01½][-–xX|/][01½][-–xX|/][01½]"
                           r"|\b(?:OD|BD|TDS|TID|QID|HS|SOS|STAT|BID|QDS)\b)", s, re.I)
    dose_text = s[dose_start.start():] if dose_start else ""
    name = s[:dose_start.start()] if dose_start else s
    if strength_m and (not dose_start or strength_m.start() < dose_start.start()):
        name = s[:strength_m.start()]
    name = name.strip(" .:-")
    return name, strength, dose_text


def _build(raw_line, read_name, strength, dose_text) -> Medicine:
    dose = dosing_mod.parse_dose(dose_text)
    m = med_mod.match(read_name)
    return Medicine(
        raw_line=raw_line,
        read_name=read_name,
        name=m.name,
        ingredient=m.ingredient,
        strength=strength,
        dose=dose,
        confidence=m.score,
        matched=m.matched,
    )


def _collect_unreadable(rx: Prescription):
    rx.unreadable = [m.read_name for m in rx.medicines if not m.matched]
