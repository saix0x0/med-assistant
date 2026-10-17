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
The Sarvam SDK is already installed and a `.env` exists. Just add your key:

```bash
# 1. open .env and paste your key after SARVAM_API_KEY=
# 2. prove one live Sarvam call works (chat, sarvam-105b-conversations):
.venv/bin/python hello_sarvam.py
# 3. (optional) test Vision on a real prescription photo:
.venv/bin/python tests/smoke_sarvam.py prescription.jpg
# 4. run the full app live:
.venv/bin/python -m uvicorn app.main:app --port 8077
```

`MODE=sarvam` is already set in `.env`; the app stays in mock automatically until a
key is present, so nothing breaks before the key is pasted. Only
`app/providers/sarvam.py` touches the Sarvam SDK — the rest is model-agnostic.

## How it fits together
`UI → FastAPI → provider (mock | Sarvam) → deterministic core → spoken output`

- **Sarvam Vision** reads the image · **Sarvam-105B** structures it ·
  **Bulbul** speaks · **Saaras** hears voice questions.
- A rule-based matcher validates every medicine against a real Indian-drug list,
  so OCR noise is corrected and invented drugs are refused.

Full write-up: [`REPORT.md`](REPORT.md) · Build-day notes: [`CONTEXT.md`](CONTEXT.md)
