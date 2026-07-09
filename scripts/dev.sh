#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_PORT="8710"
WEB_PORT="5179"
API_PID=""
WEB_PID=""

cleanup() {
  echo ""
  echo "Stopping VidTone dev servers..."
  if [[ -n "${API_PID}" ]] && kill -0 "${API_PID}" 2>/dev/null; then
    kill "${API_PID}" 2>/dev/null || true
  fi
  if [[ -n "${WEB_PID}" ]] && kill -0 "${WEB_PID}" 2>/dev/null; then
    kill "${WEB_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

if [[ ! -d "${ROOT_DIR}/.venv" ]]; then
  echo "Missing .venv. Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && pip install -e ."
  exit 1
fi

if ! command -v bun >/dev/null 2>&1; then
  echo "Missing bun. Install Bun first: https://bun.sh"
  exit 1
fi

if lsof -nP -iTCP:${API_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port ${API_PORT} is already in use. Stop that process or change API_PORT in scripts/dev.sh."
  exit 1
fi

if lsof -nP -iTCP:${WEB_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port ${WEB_PORT} is already in use. Stop that process or change WEB_PORT in scripts/dev.sh."
  exit 1
fi

cd "${ROOT_DIR}"
source "${ROOT_DIR}/.venv/bin/activate"

echo "Starting FastAPI on http://127.0.0.1:${API_PORT}"
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port "${API_PORT}" --reload &
API_PID="$!"

cd "${ROOT_DIR}/apps/web"
if [[ ! -d "node_modules" ]]; then
  echo "Installing web dependencies with Bun..."
  bun install
fi

echo "Starting React/Vite on http://127.0.0.1:${WEB_PORT}"
bun run dev &
WEB_PID="$!"

echo ""
echo "VidTone dev is running:"
echo "  Web:      http://127.0.0.1:${WEB_PORT}"
echo "  API:      http://127.0.0.1:${API_PORT}"
echo "  API docs: http://127.0.0.1:${API_PORT}/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

wait "${API_PID}" "${WEB_PID}"
