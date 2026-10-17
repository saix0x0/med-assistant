# Med Assistant

**Read, understand and verify medicines — by voice, in your language.**
Built for Sarvam Campus '26 × IIIT Hyderabad on Sarvam's AI stack.

Point a camera at a handwritten prescription or a medicine strip. The app reads
it, speaks it back in **Telugu / Hindi / English**, and **cross-checks the strip
against your prescription** — warning you if a tablet is wrong or expired.

Three tailored modes over one engine: **Patient** (low-vision, voice-first),
**Caretaker / Nurse** (schedule + dose log), **Quick read** (plain-language in 10s).

> Reads and matches only. **Not medical advice.**

## Quick start (no keys needed — runs in mock mode)
```bash
./run.sh
# open http://localhost:8000   (use :8077 if 8000 is busy)
```

## Run the tests
```bash
.venv/bin/python -m pytest -q
```

## Go live on Sarvam
```bash
cp .env.example .env          # paste SARVAM_API_KEY, set MODE=sarvam
pip install -U sarvamai
MODE=sarvam .venv/bin/python tests/smoke_sarvam.py prescription.jpg
```
Only `app/providers/sarvam.py` touches the Sarvam SDK — the rest is model-agnostic.

## How it fits together
`UI → FastAPI → provider (mock | Sarvam) → deterministic core → spoken output`

- **Sarvam Vision** reads the image · **Sarvam-105B** structures it ·
  **Bulbul** speaks · **Saaras** hears voice questions.
- A rule-based matcher validates every medicine against a real Indian-drug list,
  so OCR noise is corrected and invented drugs are refused.

Full write-up: [`REPORT.md`](REPORT.md) · Build-day notes: [`CONTEXT.md`](CONTEXT.md)
