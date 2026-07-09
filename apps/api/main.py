from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import requests
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

FALLBACK_FIREWORKS_MODELS: list[dict[str, object]] = [
    {
        "id": "accounts/fireworks/models/gpt-oss-120b",
        "name": "accounts/fireworks/models/gpt-oss-120b",
        "display_name": "gpt-oss-120b (verified)",
        "source": "fallback",
    },
    {
        "id": "accounts/fireworks/models/gpt-oss-20b",
        "name": "accounts/fireworks/models/gpt-oss-20b",
        "display_name": "gpt-oss-20b",
        "source": "fallback",
    },
]

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


def _normalize_model_item(item: object) -> dict[str, object] | None:
    if not isinstance(item, dict):
        return None

    raw_name = (
        item.get("name")
        or item.get("id")
        or item.get("model")
        or item.get("model_id")
    )
    if not raw_name:
        return None

    name = str(raw_name)
    if name.startswith("models/"):
        name = f"accounts/fireworks/{name}"
    elif not name.startswith("accounts/") and "/models/" not in name:
        name = f"accounts/fireworks/models/{name}"

    display_name = (
        item.get("displayName")
        or item.get("display_name")
        or item.get("title")
        or name.rsplit("/", 1)[-1]
    )

    base_details = item.get("baseModelDetails") if isinstance(item.get("baseModelDetails"), dict) else {}
    model_type = base_details.get("modelType") if isinstance(base_details, dict) else None

    return {
        "id": name,
        "name": name,
        "display_name": str(display_name),
        "context_length": item.get("contextLength") or item.get("context_length"),
        "model_type": model_type,
        "supports_image_input": item.get("supportsImageInput") or item.get("supports_image_input"),
        "supports_tools": item.get("supportsTools") or item.get("supports_tools"),
        "supports_serverless": item.get("supportsServerless") or item.get("supports_serverless"),
        "kind": item.get("kind"),
        "state": item.get("state"),
        "source": "fireworks",
    }


def _dedupe_models(models: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    deduped: list[dict[str, object]] = []
    for model in models:
        name = str(model.get("name") or model.get("id") or "")
        if not name or name in seen:
            continue
        seen.add(name)
        deduped.append(model)
    return deduped


def _extract_models(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        raw_models = payload
    elif isinstance(payload, dict):
        raw_models = (
            payload.get("models")
            or payload.get("data")
            or payload.get("items")
            or []
        )
    else:
        raw_models = []

    models = [_normalize_model_item(item) for item in raw_models]
    return [model for model in models if model is not None]


def _is_chat_serverless(model: dict[str, object]) -> bool:
    """Filter to models that are (a) callable via serverless chat completions
    and (b) actually a text generation model. This drops image generation
    (Flux), embeddings (Qwen embed/rerank), and custom deployments that are
    not directly invocable via /inference/v1/chat/completions.
    """
    if not model.get("supports_serverless"):
        return False
    if model.get("kind") not in {"HF_BASE_MODEL"}:
        return False
    state = model.get("state")
    if state is not None and state != "READY":
        return False
    return True


def _paginate_account_catalog(
    api_key: str,
    account_id: str,
    page_size: int = 200,
    max_pages: int = 5,
) -> list[dict[str, object]]:
    """Fetch the full Fireworks model catalog for an account, following
    ``nextPageToken`` up to ``max_pages`` times (safety cap so a runaway
    pagination doesn't stall the API).
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    base = f"https://api.fireworks.ai/v1/accounts/{account_id}/models"
    all_models: list[dict[str, object]] = []
    page_token = ""
    for _ in range(max_pages):
        params = f"?pageSize={page_size}"
        if page_token:
            params += f"&pageToken={page_token}"
        response = requests.get(base + params, headers=headers, timeout=20)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            break
        all_models.extend(_extract_models(payload))
        page_token = payload.get("nextPageToken") or ""
        if not page_token:
            break
    return all_models


def _fetch_fireworks_models(config: AppConfig) -> tuple[list[dict[str, object]], str]:
    if not config.fireworks_api_key:
        return list(FALLBACK_FIREWORKS_MODELS), "fallback:no_api_key"

    account_id = config.fireworks_account_id or "fireworks"

    # Prefer the account catalog (paginated) because it exposes the full
    # list of serverless chat models — 12+ vs the ~6–7 in the inference
    # models endpoint. We filter it to genuinely usable chat models below.
    try:
        catalog = _paginate_account_catalog(
            config.fireworks_api_key, account_id, page_size=200, max_pages=5
        )
        chat_models = [m for m in catalog if _is_chat_serverless(m)]
        if chat_models:
            # Merge with hard-coded fallbacks so gpt-oss-120b / gpt-oss-20b
            # always appear even if Fireworks changes the catalog shape.
            fallback_names = {str(item["name"]) for item in FALLBACK_FIREWORKS_MODELS}
            existing_names = {str(m["name"]) for m in chat_models}
            merged = list(chat_models) + [
                item for item in FALLBACK_FIREWORKS_MODELS
                if str(item["name"]) in fallback_names
                and str(item["name"]) not in existing_names
            ]
            return _dedupe_models(merged), f"account:{account_id}"
    except requests.RequestException:
        pass
    except ValueError:
        pass

    # Fallback: the older /inference/v1/models endpoint. Still returns a
    # useful subset when the account catalog is unreachable.
    headers = {"Authorization": f"Bearer {config.fireworks_api_key}"}
    urls = [
        "https://api.fireworks.ai/inference/v1/models",
    ]

    last_error = ""
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            models = _extract_models(response.json())
            # /inference/v1/models does not include supportsServerless flags,
            # so we cannot filter reliably. Drop obvious non-chat models by
            # name so image generators (flux-*) don't pollute the picker.
            models = [m for m in models if "flux" not in str(m.get("name", "")).lower()]
            if models:
                fallback_names = {str(item["name"]) for item in FALLBACK_FIREWORKS_MODELS}
                merged = models + [
                    item for item in FALLBACK_FIREWORKS_MODELS
                    if str(item["name"]) not in {str(model["name"]) for model in models}
                ]
                return _dedupe_models(merged), url
        except requests.RequestException as exc:
            last_error = str(exc)
            continue
        except ValueError as exc:
            last_error = f"invalid JSON: {exc}"
            continue

    return list(FALLBACK_FIREWORKS_MODELS), f"fallback:{last_error or 'no_models'}"


@app.get("/api/models")
def list_models() -> dict[str, object]:
    config = AppConfig.from_env()
    models, source = _fetch_fireworks_models(config)
    return {
        "models": models,
        "source": source,
        "default_model": config.fireworks_model or "accounts/fireworks/models/gpt-oss-120b",
        "account_id": config.fireworks_account_id,
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
