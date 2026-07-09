# Web Stack

## Decision

Use a product-style web app instead of a desktop wrapper.

```text
Frontend: React + Vite + TypeScript + Bun
Backend: FastAPI + Python
AI core: existing VidTonePipeline
```

## Why not Tauri

Tauri is better for a desktop app. This hackathon needs a web demo, application URL, API surface, and container-friendly runtime. A browser-based app is a better fit.

## Why not only Gradio

Gradio is useful for quick ML demos, but this project needs a more product-like upload/result/QA workflow. The chosen stack keeps Python for AI and gives us full control over the frontend.

## Ports

```text
API: 8710
Web: 5179
```

These are intentionally non-default to avoid common local conflicts:

```text
Vite default: 5173
Streamlit default: 8501
Common backend defaults: 8000, 3000, 5000
```

## Run

Run both API and web from the repo root:

```bash
bun run dev
```

Open:

```text
http://127.0.0.1:5179
```

API docs:

```text
http://127.0.0.1:8710/docs
```

## API endpoints

```text
GET  /health
POST /api/caption
GET  /api/export?path=<output-file-path>
```

## Frontend flow

```text
choose video
→ POST /api/caption
→ render 4 caption cards
→ show accuracy/tone/hallucination scores
→ download JSON/CSV
```
