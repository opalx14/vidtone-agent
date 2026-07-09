"""Optional long-video auto-segmentation runner (P1).

Track 2 of the AMD Developer Hackathon Act-II targets short clips
(30–120 s). When a user opts in with ``--auto-segment``, this module
splits a long video into fixed-length ``.mp4`` chunks, runs the existing
:class:`~vidtone.core.pipeline.VidTonePipeline` on each chunk in parallel,
and produces aggregate JSON / CSV / manifest artifacts alongside per-segment
outputs::

    <output_dir>/
    ├── manifest.json
    ├── segment_results.json
    ├── segment_results.csv
    ├── segments/
    │   ├── segment_001.mp4
    │   ├── segment_002.mp4
    │   └── ...
    └── per_segment/
        ├── segment_001.json           # slim summary keyed by segment_id
        ├── segment_001/               # untouched pipeline artifacts
        │   ├── <stem>_vidtone.json
        │   ├── <stem>_vidtone.csv
        │   └── <stem>_keyframes/
        ├── segment_002.json
        └── ...

Failure isolation: if one segment blows up, its traceback lands in
``manifest["failures"]`` and the rest of the segments keep running.
"""

from __future__ import annotations

import concurrent.futures
import csv
import math
import time
import traceback
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from vidtone.core.config import AppConfig
from vidtone.core.pipeline import VidTonePipeline
from vidtone.storage.exporter import write_json


# CSV column order matches the spec (`plan2.md` → P1 output structure).
SEGMENT_CSV_FIELDS = [
    "source_video",
    "segment_id",
    "start_seconds",
    "end_seconds",
    "segment_duration_seconds",
    "mode",
    "model",
    "style",
    "caption",
    "accuracy_score",
    "tone_score",
    "hallucination_risk",
    "judge_notes",
    "needs_revision",
    "original_caption",
    "final_caption",
]


def split_video(
    video_path: Path,
    output_dir: Path,
    segment_seconds: int = 60,
) -> list[dict[str, Any]]:
    """Split ``video_path`` into consecutive ``.mp4`` segments.

    Uses OpenCV's ``VideoWriter`` with the ``mp4v`` fourcc, which is what
    the CLI's ``make-sample`` command already relies on, so the codec
    availability story is consistent across the project.

    Frames are copied sequentially from the source to the current segment
    writer to avoid the seek reliability problems some containers have when
    calling ``CAP_PROP_POS_FRAMES`` on non-keyframes.

    :param video_path: Source video to segment.
    :param output_dir: Root output directory. Segments land under
        ``output_dir/segments/``.
    :param segment_seconds: Target duration in seconds per segment. The last
        segment can be shorter if the total duration is not an exact
        multiple of ``segment_seconds``.
    :returns: List of segment metadata dicts with keys ``segment_id``,
        ``path``, ``start_seconds``, ``end_seconds``, ``duration_seconds``.
    :raises RuntimeError: When OpenCV cannot open the source video, when
        core metadata is unreadable, or when the ``mp4v`` writer fails to
        open (usually a codec issue on some macOS builds).
    """
    try:
        import cv2  # type: ignore
    except ImportError as exc:  # pragma: no cover - cv2 is a required dep
        raise RuntimeError(
            "OpenCV (cv2) is required for video segmentation but is not installed."
        ) from exc

    source = Path(video_path)
    if not source.exists():
        raise RuntimeError(f"Video not found for segmentation: {source}")

    segments_dir = Path(output_dir) / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError(
            f"OpenCV could not open video for segmentation: {source}"
        )

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

    if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
        capture.release()
        raise RuntimeError(
            "Unable to read video metadata for segmentation "
            f"(fps={fps}, frames={frame_count}, resolution={width}x{height}). "
            f"Check that the file is a valid video: {source}"
        )

    segment_frames = max(1, int(round(segment_seconds * fps)))
    total_segments = max(1, math.ceil(frame_count / segment_frames))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    written_segments: dict[int, dict[str, Any]] = {}

    current_seg_idx = -1
    current_writer = None
    current_seg_path: Path | None = None
    frame_idx = 0

    try:
        while True:
            success, frame = capture.read()
            if not success:
                break

            seg_idx = min(frame_idx // segment_frames, total_segments - 1)
            if seg_idx != current_seg_idx:
                # Close previous segment writer before opening the next one.
                if current_writer is not None:
                    current_writer.release()

                current_seg_idx = seg_idx
                seg_id = f"segment_{seg_idx + 1:03d}"
                current_seg_path = segments_dir / f"{seg_id}.mp4"
                current_writer = cv2.VideoWriter(
                    str(current_seg_path),
                    fourcc,
                    fps,
                    (width, height),
                )
                if not current_writer.isOpened():
                    raise RuntimeError(
                        f"cv2.VideoWriter failed to open for {current_seg_path}. "
                        "The mp4v codec may not be available in this OpenCV build. "
                        "On macOS you may need to reinstall opencv-python or use a "
                        "different codec build."
                    )

                start_frame = seg_idx * segment_frames
                end_frame = min(start_frame + segment_frames, frame_count)
                written_segments[seg_idx] = {
                    "segment_id": seg_id,
                    "path": str(current_seg_path),
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                }

            current_writer.write(frame)
            frame_idx += 1
    finally:
        if current_writer is not None:
            current_writer.release()
        capture.release()

    if not written_segments:
        raise RuntimeError(
            f"Segmentation produced zero segments for {source}. "
            "The video may be empty or unreadable."
        )

    # Build the ordered result list. We stick with the frame plan we recorded
    # while writing rather than re-deriving from disk timestamps, so the
    # boundaries stay exact and reproducible even when the last segment is
    # partial (e.g. 30s tail after two 60s segments).
    ordered: list[dict[str, Any]] = []
    for idx in sorted(written_segments.keys()):
        info = written_segments[idx]
        start_seconds = info["start_frame"] / fps
        end_seconds = info["end_frame"] / fps
        duration_seconds = (info["end_frame"] - info["start_frame"]) / fps
        ordered.append(
            {
                "segment_id": info["segment_id"],
                "path": info["path"],
                "start_seconds": round(start_seconds, 2),
                "end_seconds": round(end_seconds, 2),
                "duration_seconds": round(duration_seconds, 2),
            }
        )
    return ordered


def _slim_segment_result(
    result: dict[str, Any],
    segment_dict: dict[str, Any],
    source_video: str,
) -> dict[str, Any]:
    """Compact per-segment summary, patterned on ``batch._slim_result``.

    Keeps the fields judges care about (segment window, mode, model,
    captions, judge scores, needs_revision) and drops verbose fields
    (``video_context``, per-frame keyframe paths) which stay accessible in
    the isolated per-segment output folder if needed.
    """
    captions = result.get("captions", {}) or {}
    return {
        "segment_id": segment_dict["segment_id"],
        "source_video": source_video,
        "filename": (result.get("video") or {}).get("filename"),
        "duration_seconds": (result.get("video") or {}).get("duration_seconds"),
        "start_seconds": segment_dict["start_seconds"],
        "end_seconds": segment_dict["end_seconds"],
        "segment_duration_seconds": segment_dict["duration_seconds"],
        "mode": result.get("mode"),
        "model": result.get("model"),
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


def _write_segment_csv(
    results: list[dict[str, Any]],
    source_video: str,
    output_path: Path,
) -> Path:
    """Emit ``segment_results.csv`` — one row per (segment × style).

    Header order is fixed via :data:`SEGMENT_CSV_FIELDS` so downstream
    leaderboard scripts can rely on a stable schema.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=SEGMENT_CSV_FIELDS)
        writer.writeheader()
        for result in results:
            seg_meta = result.get("segment_meta") or {}
            mode = result.get("mode", "")
            model = result.get("model") or ""
            for style, item in (result.get("captions") or {}).items():
                final_text = item.get("text", "")
                writer.writerow(
                    {
                        "source_video": source_video,
                        "segment_id": result.get("segment_id", ""),
                        "start_seconds": seg_meta.get("start_seconds", ""),
                        "end_seconds": seg_meta.get("end_seconds", ""),
                        "segment_duration_seconds": seg_meta.get(
                            "duration_seconds", ""
                        ),
                        "mode": mode,
                        "model": model,
                        "style": style,
                        "caption": final_text,
                        "accuracy_score": item.get("accuracy_score", ""),
                        "tone_score": item.get("tone_score", ""),
                        "hallucination_risk": item.get("hallucination_risk", ""),
                        "judge_notes": item.get("notes", ""),
                        "needs_revision": bool(item.get("needs_revision", False)),
                        "original_caption": item.get("original_caption") or "",
                        "final_caption": final_text,
                    }
                )
    return path


def _process_segment(
    config: AppConfig,
    segment_dict: dict[str, Any],
    per_segment_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any] | None, Exception | None, float]:
    """Run the pipeline for one segment and package the outcome.

    Returns a tuple ``(segment_dict, raw_result, exception, elapsed)``.
    Exactly one of ``raw_result`` and ``exception`` is populated so the
    caller can dispatch success vs failure without another try/except.
    """
    segment_id = segment_dict["segment_id"]
    segment_output = per_segment_dir / segment_id
    segment_output.mkdir(parents=True, exist_ok=True)

    # Redirect this segment's pipeline artifacts (keyframes, per-file JSON)
    # into per_segment/<segment_id>/ so parallel workers cannot clobber each
    # other's outputs. The upload_dir stays shared because we never write to
    # it here — the segment .mp4 is already on disk from split_video.
    segment_config = replace(config, output_dir=segment_output)

    start = time.monotonic()
    try:
        pipeline = VidTonePipeline(segment_config)
        raw_result = pipeline.run(Path(segment_dict["path"]))
        elapsed = round(time.monotonic() - start, 2)
        return segment_dict, raw_result, None, elapsed
    except Exception as exc:  # noqa: BLE001 - failure isolation is intentional
        elapsed = round(time.monotonic() - start, 2)
        return segment_dict, None, exc, elapsed


def run_segmented_video(
    config: AppConfig,
    video_path: Path,
    output_dir: Path,
    segment_seconds: int = 60,
    max_workers: int = 2,
) -> dict[str, Any]:
    """Split ``video_path`` and run the pipeline on each segment.

    Concurrency is bounded to ``min(max(1, max_workers), 3)`` because each
    segment can trigger up to 8+ Fireworks calls (4 captions + 4 judges +
    revisions), and Fireworks rate-limits aggressively on the coupon tier.

    Failure isolation: one bad segment must not kill the batch. Failures
    are recorded in ``manifest["failures"]`` and the aggregate exports are
    still written so the caller has something to inspect.
    """
    source = Path(video_path)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "segments").mkdir(parents=True, exist_ok=True)
    per_segment_dir = output_root / "per_segment"
    per_segment_dir.mkdir(parents=True, exist_ok=True)

    # 1) Split the source video into .mp4 chunks.
    segment_dicts = split_video(
        source, output_root, segment_seconds=segment_seconds
    )

    # 2) Clamp concurrency to a safe range.
    effective_workers = min(max(1, int(max_workers)), 3)

    mode = "mock" if not config.can_call_fireworks else "fireworks"

    manifest: dict[str, Any] = {
        "project": "VidTone Agent",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_video": str(source),
        "output_dir": str(output_root),
        "mode": mode,
        "model": config.fireworks_model,
        "vision_model": config.fireworks_vision_model,
        "segment_seconds": segment_seconds,
        "max_workers": effective_workers,
        "total": len(segment_dicts),
        "succeeded": 0,
        "failed": 0,
        "skipped": 0,
        "durations_seconds": {},
        "successes": [],
        "failures": [],
    }

    results: list[dict[str, Any]] = []

    # 3) Fan out over segments. We iterate ``futures`` in submission order
    #    (via ``future.result()``) so the aggregate CSV stays deterministic
    #    even though the underlying pipeline calls run in parallel.
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=effective_workers
    ) as executor:
        futures = [
            executor.submit(_process_segment, config, segment_dict, per_segment_dir)
            for segment_dict in segment_dicts
        ]

        for future in futures:
            segment_dict, raw_result, exc, elapsed = future.result()
            segment_id = segment_dict["segment_id"]

            if exc is not None or raw_result is None:
                manifest["failed"] += 1
                manifest["failures"].append(
                    {
                        "segment_id": segment_id,
                        "path": segment_dict["path"],
                        "elapsed_seconds": elapsed,
                        "error": f"{type(exc).__name__}: {exc}"
                        if exc is not None
                        else "unknown error",
                        "traceback": traceback.format_exception_only(
                            type(exc), exc
                        )
                        if exc is not None
                        else None,
                    }
                )
                continue

            # Enrich the pipeline result with segment metadata so the CSV
            # writer and slim summary can pull everything from one place.
            raw_result["segment_id"] = segment_id
            raw_result["source_video"] = str(source)
            raw_result["segment_meta"] = {
                "start_seconds": segment_dict["start_seconds"],
                "end_seconds": segment_dict["end_seconds"],
                "duration_seconds": segment_dict["duration_seconds"],
                "path": segment_dict["path"],
            }
            results.append(raw_result)

            manifest["succeeded"] += 1
            manifest["durations_seconds"][segment_id] = elapsed
            manifest["successes"].append(
                {
                    "segment_id": segment_id,
                    "filename": Path(segment_dict["path"]).name,
                    "path": segment_dict["path"],
                    "elapsed_seconds": elapsed,
                    "start_seconds": segment_dict["start_seconds"],
                    "end_seconds": segment_dict["end_seconds"],
                    "duration_seconds": segment_dict["duration_seconds"],
                    "mode": raw_result.get("mode"),
                    "model": raw_result.get("model"),
                    "warnings": raw_result.get("warnings", []),
                }
            )

            # Slim per-segment summary keyed by segment_id, matches the shape
            # batch.py uses for per_video/<video_id>.json.
            write_json(
                _slim_segment_result(raw_result, segment_dict, str(source)),
                per_segment_dir / f"{segment_id}.json",
            )

    # 4) Aggregate exports. These are written even when every segment failed
    #    so a partial artifact tree is still available for debugging.
    segment_json_path = write_json(
        {"results": results}, output_root / "segment_results.json"
    )
    segment_csv_path = _write_segment_csv(
        results, str(source), output_root / "segment_results.csv"
    )
    manifest_path = write_json(manifest, output_root / "manifest.json")

    return {
        "segmented": True,
        "source_video": str(source),
        "segments": len(segment_dicts),
        "succeeded": manifest["succeeded"],
        "failed": manifest["failed"],
        "total": len(segment_dicts),
        "mode": mode,
        "model": config.fireworks_model,
        "exports": {
            "segment_json": str(segment_json_path),
            "segment_csv": str(segment_csv_path),
            "manifest": str(manifest_path),
        },
        "manifest": manifest,
    }
