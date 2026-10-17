"""FastAPI backend. Thin: it wires HTTP requests to the provider + core.

Endpoints (all three UI modes share these):
    GET  /                 -> the single-page UI
    GET  /api/health       -> {mode, mock}  (shows whether Sarvam is live)
    POST /api/scan         -> read a prescription image/pdf -> structured + spoken
    POST /api/strip        -> read a strip -> cross-check verdict + spoken
    POST /api/ask          -> voice/text question answered from the prescription
    POST /api/log          -> record a dose taken/given
    GET  /api/log          -> the dose log
    GET  /api/state        -> the current saved prescription
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.core import crosscheck as cc
from app.core import log as dose_log
from app.core import prescription as rx_mod
from app.core import safety
from app.providers import get_provider

app = FastAPI(title="Sarvam Rx Assistant")
STATIC = Path(__file__).resolve().parent / "static"

# One saved prescription for the demo (single user). A real app keys this per patient.
STATE = {"rx": None}


@app.get("/api/health")
def health():
    return {"mode": config.MODE, "mock": config.is_mock(),
            "provider": get_provider().name,
            "tts": config.TTS_PROVIDER,
            "models": {"chat": config.CHAT_MODEL, "tts": config.TTS_MODEL,
                       "stt": config.STT_MODEL}}


@app.post("/api/scan")
async def scan(file: UploadFile = File(...),
               language: str = Form("en-IN"),
               content_type: str = Form("handwritten")):
    provider = get_provider()
    data = await file.read()
    raw = provider.read_document(data, file.filename or "upload.png",
                                 content_type=content_type, language=language)
    assisted = provider.assist_extract(raw)       # 105B in real mode, None in mock
    rx = rx_mod.parse(raw, assisted=assisted)      # always validated by the matcher
    STATE["rx"] = rx
    spoken = safety.speak_prescription(rx, language)
    return JSONResponse({"ok": True, "provider": provider.name,
                         "prescription": rx.to_dict(), "spoken_text": spoken})


@app.post("/api/strip")
async def strip(file: UploadFile = File(None),
                language: str = Form("en-IN"),
                scenario: str = Form("match")):
    provider = get_provider()
    data = await file.read() if file is not None else b""
    read = provider.read_strip(data, getattr(file, "filename", "strip.png") or "strip.png",
                               language=language, scenario=scenario)
    result = cc.check(read.get("name", ""), read.get("strength"),
                      read.get("expiry"), STATE["rx"])
    spoken = safety.speak_strip(result, language)
    return JSONResponse({"ok": True, "provider": provider.name,
                         "verdict": result.verdict,
                         "read": read, "spoken_text": spoken,
                         "matched": result.matched_medicine})


@app.post("/api/ask")
async def ask(question: str = Form(...), language: str = Form("en-IN")):
    provider = get_provider()
    rx = STATE["rx"]
    context = rx.raw_text if rx else ""
    answer = provider.answer(question, context, language)
    return JSONResponse({"ok": True, "answer": answer, "spoken_text": answer})


@app.post("/api/log")
async def log_dose(medicine: str = Form(...), action: str = Form("taken"),
                   actor: str = Form("patient")):
    ev = dose_log.add(medicine, action, actor)
    return JSONResponse({"ok": True, "event": ev})


@app.get("/api/log")
def get_log():
    return {"ok": True, "events": dose_log.list_events()}


@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = Form("en-IN")):
    """Voice input -> text. Uses Sarvam Saaras in live mode; in mock mode the
    browser's own recognition is used instead, so this returns a harmless
    fallback. The front-end only calls this when running live."""
    provider = get_provider()
    data = await file.read()
    text = provider.transcribe(data, language)
    return JSONResponse({"ok": True, "text": text, "provider": provider.name})


@app.get("/api/state")
def state():
    rx = STATE["rx"]
    return {"ok": True, "prescription": rx.to_dict() if rx else None}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
