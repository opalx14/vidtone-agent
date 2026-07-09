from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from vidtone.core.config import AppConfig
from vidtone.core.pipeline import VidTonePipeline
from vidtone.core.segments import run_segmented_video
from vidtone.processing.video_processor import read_video_metadata

API_PORT = 8710
WEB_PORT = 5179

# Frontend build directory. Populated by `bun run build` in apps/web.
# When the file exists, the FastAPI app serves the SPA at `/`.
# When it does not exist (dev via `bun run dev`), the Vite dev server on 5179
# proxies `/api/*` and `/health` to this API, so nothing is served here.
REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = REPO_ROOT / "apps" / "web" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"

app = FastAPI(
    title="VidTone Agent API",
    description="AI caption QA API for short videos.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{WEB_PORT}",
        f"http://127.0.0.1:{WEB_PORT}",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _safe_filename(filename: str | None) -> str:
    raw_name = Path(filename or "upload.mp4").name
    cleaned = "".join(char for char in raw_name if char.isalnum() or char in {".", "-", "_"})
    return cleaned or "upload.mp4"


def _build_request_config(use_mock: bool, model: str | None = None) -> AppConfig:
    base_config = AppConfig.from_env()
    # Only override the Fireworks model when the caller passed a non-empty
    # value. Empty string / whitespace / None all fall back to whatever is
    # in .env, preserving pre-existing behavior.
    selected_model = model.strip() if model and model.strip() else base_config.fireworks_model
    return replace(
        base_config,
        use_mock=bool(use_mock),
        fireworks_model=selected_model,
    )


@app.get("/health")
def health() -> dict[str, object]:
    config = AppConfig.from_env()
    return {
        "ok": True,
        "service": "vidtone-api",
        "api_port": API_PORT,
        "web_port": WEB_PORT,
        "mode": "fireworks" if config.can_call_fireworks else "mock-ready",
    }


@app.post("/api/caption")
async def caption_video(
    video: UploadFile = File(...),
    use_mock: bool = Form(False),
    model: str | None = Form(None),
    auto_segment: bool = Form(False),
    segment_seconds: int = Form(60),
    max_workers: int = Form(2),
) -> dict[str, object]:
    if not video.filename:
        raise HTTPException(status_code=400, detail="Missing video filename.")

    config = _build_request_config(use_mock=use_mock, model=model)
    config.ensure_dirs()

    request_id = uuid4().hex[:12]
    filename = _safe_filename(video.filename)
    video_path = config.upload_dir / f"{request_id}_{filename}"

    contents = await video.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded video is empty.")

    video_path.write_bytes(contents)

    # P1: optional long-video auto-segmentation. We only segment when the
    # caller opts in AND the uploaded video is genuinely longer than the
    # short-video target range. Short videos always fall back to the
    # verified single-pipeline path.
    if auto_segment:
        # Clamp before any pipeline call so the API can't be tricked into
        # spawning too many workers or writing extremely tiny segments.
        clamped_segment_seconds = min(max(30, int(segment_seconds)), 120)
        clamped_max_workers = min(max(1, int(max_workers)), 3)

        try:
            metadata = read_video_metadata(video_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        duration = metadata.duration_seconds

        if duration is not None and duration > config.max_video_seconds:
            segmented_output = config.output_dir / f"segmented_{request_id}"
            try:
                result = run_segmented_video(
                    config,
                    video_path,
                    segmented_output,
                    segment_seconds=clamped_segment_seconds,
                    max_workers=clamped_max_workers,
                )
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

            result["request_id"] = request_id
            return result

    try:
        result = VidTonePipeline(config).run(video_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    result["request_id"] = request_id
    return result


@app.get("/api/export")
def download_export(path: str) -> FileResponse:
    export_path = Path(path)
    if not export_path.exists() or not export_path.is_file():
        raise HTTPException(status_code=404, detail="Export file not found.")

    if export_path.suffix.lower() == ".csv":
        media_type = "text/csv"
    elif export_path.suffix.lower() == ".json":
        media_type = "application/json"
    else:
        media_type = "application/octet-stream"

    return FileResponse(export_path, media_type=media_type, filename=export_path.name)


# ---------------------------------------------------------------------------
# Static frontend mount.
#
# When `apps/web/dist/` exists (produced by `bun run build`) we mount the
# built React SPA so a single FastAPI process serves both the API and the UI
# on port 8710. This is the mode used inside Docker and on Hugging Face
# Spaces. In local dev we run `bun run dev` which uses the Vite dev server on
# port 5179 and proxies API calls back to this backend, so the mount is not
# reached.
# ---------------------------------------------------------------------------

if FRONTEND_INDEX.exists():
    # Serve hashed asset chunks under /assets/*.
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="frontend-assets",
    )

    @app.get("/")
    def frontend_index() -> FileResponse:
        return FileResponse(FRONTEND_INDEX, media_type="text/html")

    @app.get("/{path:path}")
    def frontend_catchall(path: str) -> FileResponse:
        # Try to serve any real file that lives directly under dist/ (favicon,
        # robots.txt, etc). Anything else falls back to index.html so client
        # side routing keeps working.
        candidate = FRONTEND_DIST / path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_INDEX, media_type="text/html")
