# CONTEXT — build-day handoff

Operational memory for the Sarvam Campus '26 build-along. If you (or another
agent) pick this up cold, read this first. The full rationale is in `REPORT.md`.

## What this is
Sarvam Rx Assistant: scan a prescription/strip → read + cross-check → speak it in
Telugu/Hindi/English. Three modes (Patient / Caretaker / Quick read) over one
engine. Project A2 ("Medicine Guard") from the idea shortlist.

## State as of 2026-10-17 (pre-event)
- Framework COMPLETE and running in **mock mode** (no keys). 15/15 tests pass.
- Verified end-to-end in the browser: scan parses 4 meds, Telugu output correct,
  all 4 strip verdicts render.
- **Only `app/providers/sarvam.py` needs the live key.** Nothing else changes.

## Run it
```bash
./run.sh                     # creates .venv, installs, starts on :8000
# or, if 8000 is busy:
.venv/bin/python -m uvicorn app.main:app --port 8077
```
Open http://localhost:8077 (or :8000).

## Go live at the event (the ONLY work for the 60 min)
1. `cp .env.example .env`, paste `SARVAM_API_KEY`, set `MODE=sarvam`.
2. `pip install -U sarvamai`
3. **Smoke-test Vision FIRST (biggest risk):**
   `MODE=sarvam .venv/bin/python tests/smoke_sarvam.py path/to/prescription.jpg`
4. If Vision reads handwriting → wire/confirm the 5 methods in `providers/sarvam.py`,
   tune the two prompts (assist_extract + answer).
5. Optional nicer Telugu voice: `TTS_PROVIDER=bulbul`.
6. Rehearse the 90s demo (REPORT.md §10); record a backup run.

## Sarvam models (verified ids, docs.sarvam.ai 2026-10-17)
- Vision (Document AI): `doc_ai.digitise/extract` → poll `get_status` → `get_results`.
  `content_type="handwritten"` for Rx, `"printed"` for strips. Async — seconds.
- Chat: `sarvam-105b` (JSON mode supported). `sarvam-m`/`sarvam-30b` deprecated.
- TTS: `bulbul:v3` / `bulbul:v4-flash`. STT: `saaras:v4`.
- Auth header: `api-subscription-key`. Base URL `https://api.sarvam.ai`.

## Architecture in one line
UI → FastAPI (`app/main.py`) → `get_provider()` (mock|sarvam) for the model calls
→ deterministic `app/core/*` validates everything (matcher refuses fake drugs) →
`safety.py` builds the spoken sentence. The provider seam is the whole trick.

## Known risks
- English doctor handwriting = the real unknown; smoke-test first, demo on a
  legible Rx, keep one scrawl as the honest hard case.
- Port 8000 may be taken by another local project → use 8077.
- Full ~195k Kaggle medicine CSV: drop as `app/data/indian_medicines.csv`
  (auto-loaded; gitignored). Seed list of ~50 meds ships in-repo.

## Theme alignment (say in pitch)
Hits all four Sarvam pillars: document intelligence (Vision), AI agents (105B),
multilingual (Te/Hi/En), voice (Bulbul + Saaras). India-hosted → DPDP advantage.
