#!/usr/bin/env bash
# RegWatch — one-command startup
# Works on macOS and Linux
# Requirements: Python 3.11+ (pip3)

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$SCRIPT_DIR/backend"

echo "=== RegWatch startup ==="

# ── Python venv ──────────────────────────────────────────────────────────────
if [ ! -d "$BACKEND/.venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv "$BACKEND/.venv"
fi

source "$BACKEND/.venv/bin/activate"

echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r "$BACKEND/requirements.txt"

# ── Start server ─────────────────────────────────────────────────────────────
echo ""
echo "Starting RegWatch on http://localhost:8000"
echo "Open your browser at: http://localhost:8000"
echo "(Press Ctrl+C to stop)"
echo ""

cd "$BACKEND"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
