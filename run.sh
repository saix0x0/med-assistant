#!/usr/bin/env bash
# One command to run the app. Creates the venv on first use.
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
exec .venv/bin/python -m uvicorn app.main:app --port 8077 --reload
