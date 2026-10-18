#!/usr/bin/env bash
# Start Med Assistant on http://localhost:8077 (mock mode unless .env says otherwise).
# Creates .venv on first run and keeps dependencies in sync with requirements.txt.
# Use a specific interpreter with: PYTHON=python3.11 bash run.sh
set -e
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
if [ ! -d .venv ]; then
  if ! "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
    echo "Med Assistant needs Python 3.10 or later; found $("$PY" --version 2>&1)."
    echo "Install a newer Python, then run: PYTHON=python3.11 bash run.sh"
    exit 1
  fi
  "$PY" -m venv .venv
fi
.venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt
exec .venv/bin/python -m uvicorn app.main:app --port 8077 --reload
