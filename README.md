---
title: VidTone Agent
emoji: 🎬
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 8710
pinned: false
license: mit
short_description: Multi-style video captioning with a self-judging AI agent.
---

# VidTone Agent

**Caption QA Copilot for short-video teams.** Built for **Track 2 — Video
Captioning** of the **AMD Developer Hackathon: ACT II**, hosted by LabLab.ai.

VidTone Agent turns one short video into four platform-ready caption styles
and then **judges each caption for accuracy, tone match, and hallucination
risk** before shipping. Weak captions are automatically revised.

```text
video ──▶ metadata / keyframes ──▶ CaptionAgent ──▶ JudgeAgent ──▶ revise ──▶ JSON / CSV
```

- Track: **Track 2 — Video Captioning** (LLM-judged leaderboard)
- Models: **Fireworks AI API** — verified with `gpt-oss-120b` for both the
  caption pass and the strict-JSON judge pass. Swap in a Gemma model when
  available to also enter the *Best Use of Gemma in Video Captioning* bonus.
- Runtime: **Dockerized**, single container, port `8710`

---

## Why a second agent?

Most captioning demos generate text once and hope for the best. VidTone Agent
adds a second, adversarial pass:

```text
CaptionAgent generates → JudgeAgent scores → revise if weak → export
```

The Judge Agent scores every caption on a **1–10 scale** for:

- `accuracy_score` — how faithful the caption is to the video context
- `tone_score` — how clearly the caption matches the requested style
- `hallucination_risk` — how much of the caption is unsupported invention

Anything below the revision threshold (`accuracy < 7`, `tone < 7`, or
`hallucination > 6`) is rewritten with the judge's notes as guidance and
re-scored. This is the differentiator we want the LLM judge to reward at
submission time.

## The four required styles

| Key                  | Style guide                                                    |
| -------------------- | -------------------------------------------------------------- |
| `formal`             | Professional, concise, neutral — suitable for a business report |
| `sarcastic`          | Witty and dry — not rude, not inaccurate                       |
| `humorous_tech`      | Funny for a technical audience, light software/AI metaphors    |
| `humorous_non_tech`  | Funny for a general audience, simple and accessible            |

## Features

- Product-style **web UI**: upload → preview → 4 caption cards + judge scores
- **JSON and CSV export** on every run
- **Mock mode** for API-free local demo (defaults on)
- **Fireworks AI real mode** for judged submissions
- **CLI** for scripted / batch runs
- **Single-container Docker** image that serves both the API and the SPA
- **Hugging Face Spaces** ready (Docker SDK, port `8710`)
- Health check endpoint at `/health`

## Project structure

```text
.
├── apps/
│   ├── api/main.py            # FastAPI backend + static SPA mount (port 8710)
│   ├── web/                   # React + Vite + TypeScript frontend (port 5179 in dev)
│   └── streamlit/main.py      # Legacy Streamlit UI (optional)
│
├── vidtone/                   # Core product logic
│   ├── agents/                # CaptionAgent, JudgeAgent
│   ├── clients/               # FireworksClient
│   ├── core/                  # AppConfig, VidTonePipeline
│   ├── interfaces/            # `vidtone` CLI
│   ├── processing/            # metadata + keyframe extraction
│   └── storage/               # JSON / CSV export
│
├── prompts/                   # Prompt templates for caption + judge
├── scripts/dev.sh             # One-command dev runner
├── docs/                      # Architecture, submission text, slides outline
├── samples/, outputs/, uploads/
├── Dockerfile                 # 2-stage build: Bun frontend + Python runtime
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── package.json               # exposes `bun run dev` from repo root
```

---

## Quick start — local dev (mock mode)

Requires Python 3.11+, [Bun](https://bun.sh) 1.2+, and macOS/Linux.

```bash
# 1. Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

# 2. Frontend dependencies
cd apps/web && bun install && cd ../..

# 3. Environment
cp .env.example .env    # defaults to USE_MOCK=true

# 4. One-command dev runner
bun run dev
```

Open:

- Web UI:   http://127.0.0.1:5179
- API:      http://127.0.0.1:8710
- API docs: http://127.0.0.1:8710/docs

Press `Ctrl+C` to stop both processes.

## Quick start — Docker (submission-ready)

Single container, serves both the API and the built SPA on port `8710`.

```bash
cp .env.example .env
docker compose up --build
```

Open: http://localhost:8710

The compose file mounts `outputs/`, `uploads/`, and `samples/` from the host
so generated artifacts survive container restarts.

---

## Switching to Fireworks (real mode)

See [`docs/FIREWORKS_SETUP.md`](docs/FIREWORKS_SETUP.md) for the step-by-step
guide. Short version:

1. Redeem your Fireworks coupon on https://fireworks.ai (Settings → Billing).
2. Create an API key under Settings → API Keys.
3. Pick a model slug from the Fireworks catalog. We verified
   `accounts/fireworks/models/gpt-oss-120b` end-to-end for both caption and
   strict-JSON judge output. If your account has Gemma access, swap in a
   Gemma slug to also target the partner prize.
4. Fill `.env`:
   ```env
   USE_MOCK=false
   FIREWORKS_API_KEY=fw_...
   FIREWORKS_MODEL=accounts/fireworks/models/gpt-oss-120b
   FIREWORKS_BASE_URL=https://api.fireworks.ai/inference/v1/chat/completions
   ```
5. The web UI now defaults to real Fireworks mode. Leave *Mock mode*
   unchecked to hit the model.

Verify the wiring without spending credits:

```bash
python -c "from vidtone.core.config import AppConfig; c = AppConfig.from_env(); print('can_call_fireworks =', c.can_call_fireworks)"
# → can_call_fireworks = True
```

### Best Use of Gemma via Fireworks

VidTone Agent routes both the caption pass and the strict-JSON judge pass
through whatever `FIREWORKS_MODEL` you configure. When Gemma is available on
your Fireworks account (for example `accounts/fireworks/models/gemma-3-27b-it`),
swap it in — the pipeline works identically and you become eligible for the
*Best Use of Gemma in Video Captioning* partner prize. Our reference runs
used `gpt-oss-120b` because Gemma was not available on the coupon-tier
account we tested with.

---

## CLI usage

The `vidtone` command is installed by `pip install -e .`.

```bash
# Smoke-test (no video, no API key needed)
vidtone smoke-test
python -m vidtone.interfaces.cli smoke-test

# Generate a reusable sample video
vidtone make-sample --output samples/vidtone_sample.mp4 --seconds 30 --fps 10

# Run the mock pipeline on a video
vidtone run samples/vidtone_sample.mp4 --mock --output-dir outputs

# Run against Fireworks (uses values from .env)
vidtone run samples/vidtone_sample.mp4 --real --output-dir outputs

# Or override on the command line
vidtone run video.mp4 \
    --real \
    --api-key "$FIREWORKS_API_KEY" \
    --model "$FIREWORKS_MODEL"
```

## Batch mode — the Track 2 flow

Track 2 gives every team a **fixed set of short video clips (30 s – 2 min)**
to caption. The `batch` command iterates a folder of clips, runs the full
pipeline on each, and produces aggregate JSON, CSV, and a manifest so
downstream scoring scripts have one clean handoff.

```bash
# Mock mode — no credits spent, useful for local rehearsal
vidtone batch ./clips --output outputs/batch --mock

# Fireworks / Gemma real mode
vidtone batch ./clips --output outputs/batch --real

# Optional: pass overrides on the CLI instead of via .env
vidtone batch ./clips \
    --output outputs/batch \
    --real \
    --api-key "$FIREWORKS_API_KEY" \
    --model "$FIREWORKS_MODEL" \
    --vision-model "$FIREWORKS_VISION_MODEL"

# Restrict which extensions are picked up (default covers .mp4/.mov/.webm/.mkv/.avi/.m4v)
vidtone batch ./clips --output outputs/batch --extensions .mp4,.mov --mock

# Skip per-video summary files if you only want the aggregate
vidtone batch ./clips --output outputs/batch --no-per-video --mock
```

Output tree:

```text
outputs/batch/
├── batch_results.json     # array of full per-clip results
├── batch_results.csv      # one row per (clip × style) — 4 rows per clip
├── manifest.json          # total / succeeded / failed / skipped + timings
└── per_video/
    ├── video_001.json     # slim per-clip summary keyed by video_id
    ├── video_001/         # untouched pipeline artifacts + keyframes
    │   ├── <stem>_vidtone.json
    │   ├── <stem>_vidtone.csv
    │   └── <stem>_keyframes/
    ├── video_002.json
    └── ...
```

CSV columns (`vidtone/storage/exporter.py::BATCH_CSV_FIELDS`):

```text
video_id, filename, duration_seconds, mode, style, caption,
accuracy_score, tone_score, hallucination_risk, judge_notes,
needs_revision, final_caption, original_caption,
caption_source, judge_source
```

`needs_revision=True` marks captions the Judge Agent flagged as weak; the
`original_caption` column then holds the pre-revision text so you can see
what the Judge fixed.

The batch runner **isolates failures** — if one clip is corrupted, the
error goes into `manifest.failures` and the rest of the batch keeps
running. Exit code `1` is only returned when every clip in the folder
failed.

## Output format

Each run writes both JSON and CSV to `outputs/`:

```json
{
  "project": "VidTone Agent",
  "generated_at": "2026-07-07T09:00:00+00:00",
  "mode": "fireworks",
  "video": { "filename": "sample.mp4", "duration_seconds": 45.0 },
  "warnings": [],
  "video_context": "…",
  "captions": {
    "formal": {
      "text": "…",
      "source": "fireworks",
      "accuracy_score": 8,
      "tone_score": 8,
      "hallucination_risk": 2,
      "notes": "…",
      "judge_source": "fireworks"
    },
    "sarcastic":         { "…": "…" },
    "humorous_tech":     { "…": "…" },
    "humorous_non_tech": { "…": "…" }
  },
  "exports": { "json": "outputs/…", "csv": "outputs/…" }
}
```

## API

```text
GET  /health              → service status + current mode
POST /api/caption         → multipart upload (video, use_mock) → full result JSON
GET  /api/export?path=…   → download a generated JSON or CSV
```

FastAPI auto-docs live at `http://127.0.0.1:8710/docs`.

## Hackathon submission checklist

See [`docs/submission-checklist.md`](docs/submission-checklist.md) for a live
checklist against the AMD Hackathon Act-II Track 2 requirements.

## Roadmap

- Vision-based keyframe description for stronger `video_context`
- Whisper transcript path for audio-heavy clips
- Batch mode for the fixed hackathon video set
- Judge calibration set + regression report

## License

MIT.
