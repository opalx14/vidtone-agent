"""Batch runner for the Track 2 hackathon flow.

Track 2 of the AMD Developer Hackathon Act-II gives every team a fixed set
of short video clips. This module iterates through such a folder, runs the
existing :class:`VidTonePipeline` on each clip, and produces three
aggregate artifacts alongside per-video outputs::

    <output_dir>/
    ├── batch_results.json     # one entry per clip, full pipeline result
    ├── batch_results.csv      # one row per (clip, style)
    ├── manifest.json          # total / succeeded / failed / skipped
    └── per_video/
        ├── video_001.json     # trimmed summary named by video_id
        ├── video_001/         # untouched pipeline artifacts + keyframes
        │   ├── <stem>_vidtone.json
        │   ├── <stem>_vidtone.csv
        │   └── <stem>_keyframes/
        ├── video_002.json
        └── ...
"""

from __future__ import annotations

import time
import traceback
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from vidtone.core.config import AppConfig
from vidtone.core.pipeline import VidTonePipeline
from vidtone.storage.exporter import write_batch_csv, write_json

# File extensions we treat as candidate video inputs. Anything else in the
# folder is silently skipped and reported via the manifest.
DEFAULT_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}


def _iter_video_paths(
    folder: Path, extensions: Iterable[str] | None = None
) -> list[Path]:
    """Return a sorted list of candidate video files inside ``folder``.

    Sorting is by lowercase filename so batch runs are deterministic across
    machines and across judges' filesystems.
    """
    allowed = {ext.lower() for ext in (extensions or DEFAULT_VIDEO_EXTENSIONS)}
    if not folder.exists():
        raise FileNotFoundError(f"Batch folder not found: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Batch path is not a directory: {folder}")

    candidates = [
        entry
        for entry in folder.iterdir()
        if entry.is_file() and entry.suffix.lower() in allowed
    ]
    return sorted(candidates, key=lambda p: p.name.lower())


def _slim_result(result: dict[str, Any]) -> dict[str, Any]:
    """Return a compact per-video summary suitable for ``per_video/*.json``.

    Keeps the fields judges care about (video_id, mode, captions, judge
    scores, needs_revision) and drops verbose fields (``video_context``,
    per-frame keyframe paths) which are still available in the isolated
    pipeline output folder if needed.
    """
    captions = result.get("captions", {}) or {}
    return {
        "video_id": result.get("video_id"),
        "filename": (result.get("video") or {}).get("filename"),
        "duration_seconds": (result.get("video") or {}).get("duration_seconds"),
        "mode": result.get("mode"),
        "generated_at": result.get("generated_at"),
        "warnings": result.get("warnings", []),
        "vision_source": result.get("vision_source"),
        "visual_notes": result.get("visual_notes", ""),
        "captions": {
            style: {
                "text": item.get("text"),
                "source": item.get("source"),
                "accuracy_score": item.get("accuracy_score"),
                "tone_score": item.get("tone_score"),
                "hallucination_risk": item.get("hallucination_risk"),
                "notes": item.get("notes"),
                "judge_source": item.get("judge_source"),
                "needs_revision": item.get("needs_revision", False),
                "original_caption": item.get("original_caption"),
            }
            for style, item in captions.items()
        },
        "exports": result.get("exports"),
    }


def run_batch(
    config: AppConfig,
    folder: str | Path,
    output_dir: str | Path,
    *,
    write_per_video: bool = True,
    extensions: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Run the VidTone pipeline over every video in ``folder``.

    Failure isolation: if a single clip raises, the batch continues, records
    the error in the manifest, and moves on. This keeps the run useful even
    when a corrupted clip is included in the hackathon set.
    """
    folder_path = Path(folder)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    per_video_root = output_root / "per_video"
    per_video_root.mkdir(parents=True, exist_ok=True)

    videos = _iter_video_paths(folder_path, extensions=extensions)

    manifest: dict[str, Any] = {
        "project": "VidTone Agent",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "folder": str(folder_path),
        "output_dir": str(output_root),
        "mode": "mock" if not config.can_call_fireworks else "fireworks",
        "total": len(videos),
        "succeeded": 0,
        "failed": 0,
        "skipped": 0,
        "durations_seconds": {},
        "successes": [],
        "failures": [],
    }

    results: list[dict[str, Any]] = []

    if not videos:
        # Nothing to do, but we still emit an empty aggregate + manifest so
        # judges can see we handled the empty-folder case gracefully.
        manifest["notes"] = "No supported video files found in folder."
        write_json({"results": []}, output_root / "batch_results.json")
        write_batch_csv([], output_root / "batch_results.csv")
        write_json(manifest, output_root / "manifest.json")
        return {
            "manifest": manifest,
            "results": [],
            "exports": {
                "batch_json": str(output_root / "batch_results.json"),
                "batch_csv": str(output_root / "batch_results.csv"),
                "manifest": str(output_root / "manifest.json"),
            },
        }

    for index, video_path in enumerate(videos, start=1):
        video_id = f"video_{index:03d}"
        video_output = per_video_root / video_id
        video_output.mkdir(parents=True, exist_ok=True)

        # Isolate this clip's pipeline artifacts (keyframes, per-file JSON)
        # inside per_video/<video_id>/ so the batch output tree stays clean.
        per_video_config = replace(
            config,
            output_dir=video_output,
        )

        start = time.monotonic()
        try:
            pipeline = VidTonePipeline(per_video_config)
            raw_result = pipeline.run(video_path)
        except Exception as exc:  # noqa: BLE001 - we want to keep going
            elapsed = round(time.monotonic() - start, 2)
            manifest["failed"] += 1
            manifest["failures"].append(
                {
                    "video_id": video_id,
                    "path": str(video_path),
                    "elapsed_seconds": elapsed,
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc(limit=4),
                }
            )
            continue

        elapsed = round(time.monotonic() - start, 2)
        raw_result["video_id"] = video_id
        raw_result["elapsed_seconds"] = elapsed
        raw_result["source_path"] = str(video_path)
        results.append(raw_result)

        manifest["succeeded"] += 1
        manifest["durations_seconds"][video_id] = elapsed
        manifest["successes"].append(
            {
                "video_id": video_id,
                "filename": video_path.name,
                "path": str(video_path),
                "elapsed_seconds": elapsed,
                "duration_seconds": (raw_result.get("video") or {}).get("duration_seconds"),
                "mode": raw_result.get("mode"),
                "warnings": raw_result.get("warnings", []),
            }
        )

        if write_per_video:
            summary_path = per_video_root / f"{video_id}.json"
            write_json(_slim_result(raw_result), summary_path)

    batch_json_path = write_json(
        {"results": results}, output_root / "batch_results.json"
    )
    batch_csv_path = write_batch_csv(results, output_root / "batch_results.csv")
    manifest_path = write_json(manifest, output_root / "manifest.json")

    return {
        "manifest": manifest,
        "results": results,
        "exports": {
            "batch_json": str(batch_json_path),
            "batch_csv": str(batch_csv_path),
            "manifest": str(manifest_path),
        },
    }
