"""Dose log — the 'verify later what was taken' record.

Deliberately simple for the demo: an in-process list, cleared on restart. In
production this becomes a small DB row per patient. The point to show is that a
record exists at all — for a blind patient with no caretaker, or for a nurse's
handover. Health data stays on an India-hosted stack (Sarvam) under the DPDP Act.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List

_ENTRIES: List[dict] = []


@dataclass
class DoseEvent:
    medicine: str
    action: str          # "taken" | "given" | "skipped"
    actor: str           # "patient" | "caretaker" | "nurse"
    at: str              # ISO timestamp


def add(medicine: str, action: str = "taken", actor: str = "patient") -> dict:
    ev = DoseEvent(medicine=medicine, action=action, actor=actor,
                   at=datetime.now().isoformat(timespec="seconds"))
    _ENTRIES.append(asdict(ev))
    return asdict(ev)


def list_events() -> List[dict]:
    return list(reversed(_ENTRIES))


def clear() -> None:
    _ENTRIES.clear()
