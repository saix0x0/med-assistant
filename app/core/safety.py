"""Builds the spoken/written sentences, in plain language, per target language.

Two reasons this is its own module:
  1. Safety wording is fixed here, in one place: we never say "safe to take",
     we always state what could not be read, and we always append a disclaimer.
  2. Multilingual templates (en-IN / hi-IN / te-IN) let the demo show real
     Telugu/Hindi output in mock mode, before Bulbul/105B are wired in. In real
     mode, 105B/Mayura can replace these templates for natural phrasing.
"""
from __future__ import annotations

from typing import Optional

from app.core import crosscheck as cc
from app.core.prescription import Prescription

LANGS = ("en-IN", "hi-IN", "te-IN")

# Minimal phrase book. Enough for the schedule vocabulary we actually produce.
_T = {
    "en-IN": {
        "n_medicines": "{n} medicines.",
        "one_medicine": "1 medicine.",
        "take": "{name}: {times}{food}{days}.",
        "morning": "morning", "noon": "afternoon", "evening": "evening", "night": "night",
        "after": " after food", "before": " before food",
        "for_days": " for {d} days", "as_needed": "as needed", "join": " and ",
        "could_not_read": "I could not read {n} item clearly. Please show it again.",
        "could_not_read_plural": "I could not read {n} items clearly. Please show them again.",
        "on_list": "{name}. This is on your prescription. Take it {times}{food}.",
        "not_on_list": "{name}. This is NOT on your prescription. Please check with your doctor.",
        "expired": "This strip, {name}, expired in {exp}. Do not use it.",
        "unreadable": "I could not read the name clearly. Please turn the strip over and hold it steady.",
        "disclaimer": "This tool only reads and matches. It is not medical advice.",
        "logged": "Noted. You took {name} at {time}.",
    },
    "hi-IN": {
        "n_medicines": "{n} दवाइयाँ।",
        "one_medicine": "1 दवाई।",
        "take": "{name}: {times}{food}{days}।",
        "morning": "सुबह", "noon": "दोपहर", "evening": "शाम", "night": "रात",
        "after": " खाने के बाद", "before": " खाने से पहले",
        "for_days": " {d} दिन तक", "as_needed": "ज़रूरत पड़ने पर", "join": " और ",
        "could_not_read": "मैं {n} चीज़ ठीक से नहीं पढ़ पाया। कृपया फिर दिखाइए।",
        "could_not_read_plural": "मैं {n} चीज़ें ठीक से नहीं पढ़ पाया। कृपया फिर दिखाइए।",
        "on_list": "{name}। यह आपके पर्चे में है। इसे {times}{food} लें।",
        "not_on_list": "{name}। यह आपके पर्चे में नहीं है। कृपया डॉक्टर से पूछें।",
        "expired": "यह पत्ता, {name}, {exp} में समाप्त हो गया। इसे न लें।",
        "unreadable": "मैं नाम ठीक से नहीं पढ़ पाया। कृपया पत्ते को पलटें और स्थिर रखें।",
        "disclaimer": "यह उपकरण केवल पढ़ता और मिलाता है। यह चिकित्सकीय सलाह नहीं है।",
        "logged": "दर्ज कर लिया। आपने {name} {time} बजे ली।",
    },
    "te-IN": {
        "n_medicines": "{n} మందులు.",
        "one_medicine": "1 మందు.",
        "take": "{name}: {times}{food}{days}.",
        "morning": "ఉదయం", "noon": "మధ్యాహ్నం", "evening": "సాయంత్రం", "night": "రాత్రి",
        "after": " భోజనం తర్వాత", "before": " భోజనానికి ముందు",
        "for_days": " {d} రోజులు", "as_needed": "అవసరమైనప్పుడు", "join": " మరియు ",
        "could_not_read": "{n} అంశం స్పష్టంగా చదవలేకపోయాను. దయచేసి మళ్లీ చూపించండి.",
        "could_not_read_plural": "{n} అంశాలు స్పష్టంగా చదవలేకపోయాను. దయచేసి మళ్లీ చూపించండి.",
        "on_list": "{name}. ఇది మీ ప్రిస్క్రిప్షన్‌లో ఉంది. దీన్ని {times}{food} తీసుకోండి.",
        "not_on_list": "{name}. ఇది మీ ప్రిస్క్రిప్షన్‌లో లేదు. దయచేసి వైద్యుడిని అడగండి.",
        "expired": "ఈ స్ట్రిప్, {name}, {exp} లో గడువు ముగిసింది. దీన్ని వాడకండి.",
        "unreadable": "పేరు స్పష్టంగా చదవలేకపోయాను. దయచేసి స్ట్రిప్‌ను తిప్పి స్థిరంగా పట్టుకోండి.",
        "disclaimer": "ఈ సాధనం కేవలం చదివి సరిపోల్చుతుంది. ఇది వైద్య సలహా కాదు.",
        "logged": "నమోదు అయింది. మీరు {name} ని {time} కి తీసుకున్నారు.",
    },
}


def _t(lang: str) -> dict:
    return _T.get(lang, _T["en-IN"])


def _times_phrase(dose, lang: str) -> str:
    t = _t(lang)
    if dose.prn:
        return t["as_needed"]
    parts = [t[slot] for slot in dose.times] or [t["morning"]]
    return t["join"].join(parts)


def _food_phrase(dose, lang: str) -> str:
    t = _t(lang)
    if dose.food == "after":
        return t["after"]
    if dose.food == "before":
        return t["before"]
    return ""


def speak_prescription(rx: Prescription, lang: str = "en-IN") -> str:
    t = _t(lang)
    n = len(rx.medicines)
    lines = [t["one_medicine"] if n == 1 else t["n_medicines"].format(n=n)]
    for med in rx.medicines:
        name = med.name or med.read_name
        if med.strength:
            name = f"{name} {med.strength}"
        days = t["for_days"].format(d=med.dose.days) if med.dose.days else ""
        lines.append(t["take"].format(
            name=name, times=_times_phrase(med.dose, lang),
            food=_food_phrase(med.dose, lang), days=days))
    if rx.unreadable:
        k = "could_not_read" if len(rx.unreadable) == 1 else "could_not_read_plural"
        lines.append(t[k].format(n=len(rx.unreadable)))
    lines.append(t["disclaimer"])
    return " ".join(lines)


def speak_strip(result: cc.StripResult, lang: str = "en-IN") -> str:
    t = _t(lang)
    name = result.name or result.read_name
    if result.strength and name:
        name = f"{name} {result.strength}"
    if result.verdict == cc.UNREADABLE:
        return t["unreadable"]
    if result.verdict == cc.EXPIRED:
        return t["expired"].format(name=name, exp=result.expiry_text or "?") + " " + t["disclaimer"]
    if result.verdict == cc.NOT_ON_LIST:
        return t["not_on_list"].format(name=name) + " " + t["disclaimer"]
    # on_list
    dose = result.matched_medicine["dose"] if result.matched_medicine else None
    times = ""
    food = ""
    if dose:
        parts = [t[s] for s in dose.get("times", [])] or [t["morning"]]
        times = t["join"].join(parts)
        if dose.get("food") == "after":
            food = t["after"]
        elif dose.get("food") == "before":
            food = t["before"]
    return t["on_list"].format(name=name, times=times, food=food) + " " + t["disclaimer"]
