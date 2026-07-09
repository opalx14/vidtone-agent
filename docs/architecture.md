# Architecture

## Components

```text
apps/web React UI, apps/api FastAPI, apps/streamlit/main.py, or vidtone/interfaces/cli.py
  -> vidtone/core/VidTonePipeline
      -> vidtone/processing/VideoProcessor functions
      -> vidtone/agents/CaptionAgent
          -> vidtone/clients/FireworksClient or mock generator
      -> vidtone/agents/JudgeAgent
          -> vidtone/clients/FireworksClient or mock judge
      -> vidtone/storage/exporter
```

## Folder roles

```text
vidtone/agents      AI decision logic: captioning, judging, revision
vidtone/clients     External service adapters: Fireworks API
vidtone/core        App configuration and pipeline orchestration
apps/api            FastAPI web backend on port 8710
apps/web            React/Vite/Bun frontend on port 5179
vidtone/interfaces  User-facing CLI entrypoints
vidtone/processing  Video/media processing
vidtone/storage     JSON/CSV export and persistence helpers
prompts             Prompt templates used by agents
```

## Data flow

1. User uploads a video.
2. The app stores the file in `uploads/`.
3. `VideoProcessor` reads metadata and extracts keyframes.
4. `build_video_context()` creates a compact text context for model prompts.
5. `CaptionAgent` generates captions for all required styles.
6. `JudgeAgent` scores each caption.
7. Low-scoring captions are revised.
8. Result is written to JSON and CSV.
9. Streamlit displays results and download buttons, or CLI prints JSON summary.

## Runtime modes

### Mock mode

Default mode. No API key required.

```bash
USE_MOCK=true
```

### Fireworks mode

Calls the configured Fireworks model.

```bash
USE_MOCK=false
FIREWORKS_API_KEY=...
FIREWORKS_MODEL=...
```

## Current limitation

The MVP does not yet transcribe audio or describe frames with a vision model. It uses video metadata and keyframe extraction as the first runnable foundation. The next high-impact improvement is to add transcription and frame-level visual summaries.
