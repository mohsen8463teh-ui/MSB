#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
else
  echo "ERROR: Python 3 was not found."
  exit 1
fi

if ! "$PYTHON" -c "import fastapi, uvicorn, httpx, pydantic" >/dev/null 2>&1; then
  echo "ERROR: Runtime dependencies are missing for: $PYTHON"
  echo "Activate the project venv and install backend/requirements.txt, then run this script again."
  exit 1
fi

echo "Starting M.S.B locally on this device."
echo "Dashboard: http://127.0.0.1:8000/"
echo "Health:    http://127.0.0.1:8000/health"
echo "TSETMC requests will run from this Termux network, not from GitHub Actions."
exec "$PYTHON" -m uvicorn backend.app.main:app --host 127.0.0.1 --port "${MSB_PORT:-8000}"
