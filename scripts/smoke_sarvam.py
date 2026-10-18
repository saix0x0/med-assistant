"""Run this FIRST at the event, right after putting the key in .env.

It checks each Sarvam API responds, Vision first (the biggest risk). It does not
touch the web app, so you learn fast whether handwriting reading works before you
wire anything. Usage:

    MODE=sarvam .venv/bin/python tests/smoke_sarvam.py path/to/prescription.jpg
"""
import sys

from app import config
from app.providers.sarvam import SarvamProvider


def main():
    if config.is_mock():
        print("Still in MOCK mode. Set MODE=sarvam and SARVAM_API_KEY in .env.")
        return
    p = SarvamProvider()
    print("Provider:", p.name, "| chat:", config.CHAT_MODEL)

    if len(sys.argv) > 1:
        path = sys.argv[1]
        with open(path, "rb") as f:
            data = f.read()
        print("\n[Vision] reading", path, "...")
        text = p.read_document(data, path, content_type="handwritten", language="en-IN")
        print("----- raw text -----\n", text[:1200])
        print("\n[105B] structuring ...")
        print(p.assist_extract(text))
    else:
        print("Tip: pass a prescription image path to test Vision.")

    print("\n[105B chat] ...")
    print(p.answer("Which tablet at night?", "Tab Dolo 650 1-0-1", "en-IN"))
    print("\nDone. If Vision returned readable text, you are ready to demo.")


if __name__ == "__main__":
    main()
