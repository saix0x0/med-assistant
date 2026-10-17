"""Real Sarvam provider. THIS is the file you finish at the event.

Everything else in the app is done. On build day:
  1. pip install -U sarvamai
  2. put SARVAM_API_KEY in .env and set MODE=sarvam
  3. run tests/smoke_sarvam.py  -> confirms each API responds (Vision first!)
  4. tune the two prompts below if needed, then demo.

Written against the verified SDK notes (docs.sarvam.ai, 2026-10-17). The calls
below are the documented shapes; the SDK import is lazy so mock mode never needs
the package installed. Anything that fails falls back gracefully so a single
flaky API cannot crash the whole demo.
"""
from __future__ import annotations

import base64
import json
import time
from typing import List, Optional

from app import config
from app.core import usage

_client = None


def _c():
    global _client
    if _client is None:
        from sarvamai import SarvamAI  # lazy: only needed in real mode
        _client = SarvamAI(api_subscription_key=config.SARVAM_API_KEY)
    return _client


# ---- Sarvam Vision (Document AI) : async job -> poll -> results -------------
def _vision(data: bytes, filename: str, content_type: str, language: str) -> str:
    import io
    client = _c()
    # content_type: "handwritten" (prescription) | "printed" (strip) | "mixed"
    start = client.doc_ai.digitise(
        file=[(filename, io.BytesIO(data), _mime(filename))],
        language=language,
        content_type=content_type,
    )
    usage.add("vision")                   # one billable Vision job
    job_id = getattr(start, "job_id", None) or start["job_id"]
    for _ in range(30):                      # poll up to ~30s
        status = client.doc_ai.get_status(job_id)
        state = getattr(status, "status", None) or status.get("status")
        if state in ("completed", "partially_completed"):
            break
        if state in ("failed", "rejected"):
            return ""
        time.sleep(1)
    # The real text lives in each page's blocks[].text. page.content is often
    # None, and the md/html/text formats can 400 or return non-utf8 bytes, so we
    # use the json result and pull the block text.
    res = client.doc_ai.get_results(job_id, format="json")
    chunks = []
    for doc in getattr(res, "documents", []) or []:
        for pg in getattr(doc, "pages", []) or []:
            c = getattr(pg, "content", None)
            if c:
                chunks.append(c)
                continue
            for b in getattr(pg, "blocks", []) or []:
                t = b.get("text") if isinstance(b, dict) else getattr(b, "text", "")
                if t:
                    chunks.append(t)
    return "\n".join(chunks).strip()


def _mime(filename: str) -> str:
    f = filename.lower()
    if f.endswith(".pdf"):
        return "application/pdf"
    if f.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    return "image/png"


class SarvamProvider:
    name = "sarvam"

    def read_document(self, data: bytes, filename: str,
                      content_type: str = "handwritten",
                      language: str = "en-IN") -> str:
        try:
            return _vision(data, filename, content_type, language)
        except Exception as e:
            return f"[vision-error] {e}"

    def read_strip(self, data: bytes, filename: str,
                   language: str = "en-IN", scenario: str = "match") -> dict:
        # Use Vision 'extract' with a schema so the strip comes back structured.
        import io
        schema = json.dumps({
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "brand name of the medicine"},
                "strength": {"type": "string", "description": "e.g. 650 mg"},
                "expiry": {"type": "string", "description": "expiry date, e.g. 03/2027"},
            },
        })
        try:
            client = _c()
            start = client.doc_ai.extract(
                file=[(filename, io.BytesIO(data), _mime(filename))],
                schema=schema, content_type="printed", language=language)
            usage.add("vision")               # one billable Vision job
            job_id = getattr(start, "job_id", None) or start["job_id"]
            for _ in range(30):
                st = client.doc_ai.get_status(job_id)
                state = getattr(st, "status", None) or st.get("status")
                if state in ("completed", "partially_completed", "failed", "rejected"):
                    break
                time.sleep(1)
            res = client.doc_ai.get_results(job_id, format="json")
            fields = _first_json(res)
            return {"name": fields.get("name", ""),
                    "strength": fields.get("strength", ""),
                    "expiry": fields.get("expiry", "")}
        except Exception:
            return {"name": "", "strength": "", "expiry": ""}

    def assist_extract(self, raw_text: str) -> Optional[List[dict]]:
        # Sarvam-105B as a structuring agent. Validated afterwards by the matcher.
        prompt = (
            "You are reading an Indian medical prescription. From the text below, "
            "list each medicine as JSON. Return ONLY JSON: "
            '{"medicines":[{"name":"","strength":"","dose":"","raw":""}]}. '
            "Keep the original dosing code (e.g. 1-0-1, BD, TDS, x5d, a/f) in "
            '"dose". Do not invent medicines.\n\nTEXT:\n' + (raw_text or ""))
        try:
            resp = _c().chat.completions(
                model=config.CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"})
            usage.add("chat", tokens=_tok(resp))
            content = resp.choices[0].message.content
            return json.loads(content).get("medicines")
        except Exception:
            return None  # fall back to deterministic parser

    def answer(self, question: str, context: str, language: str = "en-IN") -> str:
        prompt = (
            f"Answer the patient's question using ONLY this prescription. "
            f"Reply in {language}. Be short and literal. Do not give medical advice.\n\n"
            f"PRESCRIPTION:\n{context}\n\nQUESTION: {question}")
        try:
            resp = _c().chat.completions(
                model=config.CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1)
            usage.add("chat", tokens=_tok(resp))
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"[chat-error] {e}"

    def speak(self, text: str, language: str = "en-IN") -> Optional[bytes]:
        if config.TTS_PROVIDER != "bulbul":
            return None  # let the browser speak unless Bulbul is explicitly on
        try:
            resp = _c().text_to_speech.convert(
                text=text[:2400], target_language_code=language,
                model=config.TTS_MODEL)
            usage.add("tts")
            audios = getattr(resp, "audios", None) or resp["audios"]
            return base64.b64decode("".join(audios))
        except Exception:
            return None

    def transcribe(self, audio: bytes, language: str = "en-IN") -> str:
        import io
        try:
            out = _c().speech_to_text.transcribe(
                file=io.BytesIO(audio), model=config.STT_MODEL,
                mode="transcribe").transcript
            usage.add("stt")
            return out
        except Exception:
            return ""


def _tok(resp) -> int:
    """Best-effort total token count from a chat response, for the usage meter."""
    u = getattr(resp, "usage", None)
    if u is None:
        return 0
    return getattr(u, "total_tokens", 0) or 0


def _first_json(res) -> dict:
    """Pull the first structured field dict out of a doc_ai extract result."""
    for attr in ("data", "documents", "results"):
        val = getattr(res, attr, None)
        if isinstance(val, dict):
            return val
        if isinstance(val, list) and val:
            item = val[0]
            if isinstance(item, dict):
                return item
            fields = getattr(item, "fields", None) or getattr(item, "data", None)
            if isinstance(fields, dict):
                return fields
    return {}
