# Project Map: VidTone Agent

## Entry points

- `apps/api/main.py`
  - FastAPI backend on port `8710`.
  - Endpoints: `GET /health`, `POST /api/caption`, `GET /api/export?path=...`.
  - When `apps/web/dist/` exists, it also serves the built SPA at `/`.

- `apps/web/`
  - React + Vite + TypeScript frontend.
  - Bun-based dev/build runner.
  - Dev server on port `5179`, proxies `/api/*` and `/health` to the API.
  - Production build ends up in `apps/web/dist/` and is served by FastAPI.

- `apps/streamlit/main.py`
  - Legacy Streamlit UI, kept for reference. Not part of the shipped
    submission runtime.

- `vidtone/interfaces/cli.py`
  - CLI entry point registered as the `vidtone` console script.
  - Commands: `run`, `smoke-test`, `make-sample`.

## Folder roles

- `vidtone/agents/` — AI decision logic.
  - `CaptionAgent` generates and revises captions.
  - `JudgeAgent` scores accuracy, tone, and hallucination risk.
- `vidtone/clients/` — External service adapters.
  - `FireworksClient` wraps Fireworks AI chat completions.
- `vidtone/core/` — Configuration and orchestration.
  - `AppConfig` reads environment variables and resolves runtime mode.
  - `VidTonePipeline` coordinates the full video → captions flow.
- `vidtone/interfaces/` — User-facing CLI entrypoints.
- `vidtone/processing/` — Video metadata, keyframe extraction, context builder.
- `vidtone/storage/` — JSON/CSV export helpers.
- `apps/api/` — FastAPI backend + static SPA mount.
- `apps/web/` — Product-style React UI (upload, cards, exports).
- `prompts/` — Prompt templates for caption and judge agents.

## Ports

```text
FastAPI (dev and prod): 8710
Vite dev server:        5179
Streamlit legacy:       8501
```

## Common commands

```bash
# Python setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Sanity check
vidtone smoke-test
python -m vidtone.interfaces.cli smoke-test

# Frontend deps
cd apps/web && bun install && cd ../..

# Dev servers (API + Vite) in one command
bun run dev

# Or run each service manually
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8710 --reload
cd apps/web && bun run dev

# Build the frontend for containerized serving
cd apps/web && bun run build

# Sample video for the demo
vidtone make-sample --output samples/vidtone_sample.mp4 --seconds 30 --fps 10

# Full pipeline in mock mode
vidtone run samples/vidtone_sample.mp4 --mock --output-dir outputs

# Full pipeline against Fireworks
vidtone run samples/vidtone_sample.mp4 --real --output-dir outputs
```

## Docker

```bash
docker compose up --build
# → http://localhost:8710
```

The Dockerfile is a two-stage build:

1. `oven/bun:1.2-alpine` compiles the frontend into `apps/web/dist/`.
2. `python:3.11-slim` installs backend dependencies, copies the built
   frontend, and runs `uvicorn apps.api.main:app` on port `8710`.

## Environment

Runtime mode is controlled by `.env` (loaded via `python-dotenv`):

```env
USE_MOCK=true|false
FIREWORKS_API_KEY=...
FIREWORKS_MODEL=accounts/fireworks/models/gemma-3-27b-it
FIREWORKS_BASE_URL=https://api.fireworks.ai/inference/v1/chat/completions
```

`AppConfig.can_call_fireworks` becomes `True` only when `USE_MOCK=false` and
both `FIREWORKS_API_KEY` and `FIREWORKS_MODEL` are set.
