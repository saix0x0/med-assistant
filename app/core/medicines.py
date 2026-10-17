"""Medicine matcher. Pure, deterministic, no AI.

Fuzzy-matches whatever the OCR read against a known list of Indian medicines.
Two jobs:
  1. Fix OCR noise: "Doio 65O" -> "Dolo 650".
  2. Refuse to invent: if nothing is close enough, we return no match and the
     safety layer says "couldn't read this" instead of guessing a drug name.

Ships with a small seed list (data/medicines_seed.csv). Drop the full ~195k-row
Kaggle Indian-medicine CSV in data/ as 'indian_medicines.csv' (columns including
a name and a composition/ingredient) and it is loaded automatically.
"""
from __future__ import annotations

import csv
import difflib
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app import config

# Common OCR character confusions, applied before matching.
_OCR_FIXES = str.maketrans({"0": "o", "1": "l", "5": "s", "8": "b", "|": "l"})


@dataclass
class MedMatch:
    query: str
    name: Optional[str]          # canonical brand name, or None if no confident match
    ingredient: Optional[str]
    score: float                 # 0..1
    matched: bool


def _norm(s: str) -> str:
    """Lowercase, strip strength numbers/units, collapse spaces."""
    s = (s or "").lower()
    s = re.sub(r"\b\d+\s*(mg|ml|mcg|g|iu)\b", " ", s)   # drop "650 mg"
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _key(s: str) -> str:
    """Aggressive key used only for fuzzy comparison (absorbs OCR noise)."""
    return _norm(s).translate(_OCR_FIXES).replace(" ", "")


@lru_cache(maxsize=1)
def _catalog() -> list:
    """Return list of (name, ingredient, key). Seed + optional full CSV."""
    rows = []
    seed = config.DATA_DIR / "medicines_seed.csv"
    rows += _read_csv(seed)
    full = config.DATA_DIR / "indian_medicines.csv"
    if full.exists():
        rows += _read_csv(full)
    # de-dup by key, keep first
    seen, out = set(), []
    for name, ing in rows:
        k = _key(name)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append((name, ing, k))
    return out


def _read_csv(path: Path) -> list:
    if not path.exists():
        return []
    out = []
    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        fields = [c.lower() for c in (reader.fieldnames or [])]
        name_col = _pick(fields, ("name", "medicine", "brand", "product"))
        ing_col = _pick(fields, ("ingredient", "composition", "short_composition1",
                                 "salt", "generic", "composition1"))
        for row in reader:
            low = {k.lower(): v for k, v in row.items()}
            name = (low.get(name_col) or "").strip()
            ing = (low.get(ing_col) or "").strip() if ing_col else ""
            if name:
                out.append((name, ing))
    return out


def _pick(fields: list, candidates: tuple) -> Optional[str]:
    for c in candidates:
        if c in fields:
            return c
    return None


def match(query: str, threshold: float = 0.72) -> MedMatch:
    """Best match for an OCR'd medicine name, or an unmatched result."""
    q = _key(query)
    if not q:
        return MedMatch(query, None, None, 0.0, False)
    cat = _catalog()
    best_name, best_ing, best_score = None, None, 0.0
    for name, ing, k in cat:
        score = difflib.SequenceMatcher(None, q, k).ratio()
        # bonus if one contains the other (e.g. "dolo" in "dolo650")
        if q in k or k in q:
            score = max(score, 0.9)
        if score > best_score:
            best_name, best_ing, best_score = name, ing, score
    matched = best_score >= threshold
    return MedMatch(query, best_name if matched else None,
                    best_ing if matched else None, round(best_score, 3), matched)


def ingredient_of(name: str) -> Optional[str]:
    m = match(name)
    return m.ingredient
