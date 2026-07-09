from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable


def write_json(data: Any, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def write_csv(data: dict[str, Any], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    captions = data.get("captions", {})
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "style",
                "caption",
                "caption_source",
                "accuracy_score",
                "tone_score",
                "hallucination_risk",
                "judge_notes",
                "judge_source",
                "needs_revision",
                "original_caption",
            ],
        )
        writer.writeheader()
        for style, item in captions.items():
            writer.writerow(
                {
                    "style": style,
                    "caption": item.get("text", ""),
                    "caption_source": item.get("source", ""),
                    "accuracy_score": item.get("accuracy_score", ""),
                    "tone_score": item.get("tone_score", ""),
                    "hallucination_risk": item.get("hallucination_risk", ""),
                    "judge_notes": item.get("notes", ""),
                    "judge_source": item.get("judge_source", ""),
                    "needs_revision": item.get("needs_revision", False),
                    "original_caption": item.get("original_caption") or "",
                }
            )
    return path


# ---------------------------------------------------------------------------
# Batch exports — one row per (video, style). Consumed by the CLI `batch`
# command and by downstream leaderboard scripts that expect a flat CSV of
# clip → style → caption.
# ---------------------------------------------------------------------------

BATCH_CSV_FIELDS = [
    "video_id",
    "filename",
    "duration_seconds",
    "mode",
    "style",
    "caption",
    "accuracy_score",
    "tone_score",
    "hallucination_risk",
    "judge_notes",
    "needs_revision",
    "final_caption",
    "original_caption",
    "caption_source",
    "judge_source",
]


def _iter_rows(result: dict[str, Any]) -> Iterable[dict[str, Any]]:
    video = result.get("video", {}) or {}
    filename = video.get("filename", "")
    duration_seconds = video.get("duration_seconds", "")
    mode = result.get("mode", "")
    video_id = result.get("video_id", "")

    for style, item in (result.get("captions") or {}).items():
        final_text = item.get("text", "")
        yield {
            "video_id": video_id,
            "filename": filename,
            "duration_seconds": duration_seconds if duration_seconds is not None else "",
            "mode": mode,
            "style": style,
            # `caption` and `final_caption` intentionally hold the same value.
            # `caption` is the primary answer; `final_caption` is kept as a
            # separate column so downstream tooling can diff against
            # `original_caption` when needs_revision is true.
            "caption": final_text,
            "accuracy_score": item.get("accuracy_score", ""),
            "tone_score": item.get("tone_score", ""),
            "hallucination_risk": item.get("hallucination_risk", ""),
            "judge_notes": item.get("notes", ""),
            "needs_revision": bool(item.get("needs_revision", False)),
            "final_caption": final_text,
            "original_caption": item.get("original_caption") or "",
            "caption_source": item.get("source", ""),
            "judge_source": item.get("judge_source", ""),
        }


def write_batch_csv(results: list[dict[str, Any]], output_path: str | Path) -> Path:
    """Write a batch-level CSV with one row per (video, style).

    Each element of ``results`` is expected to look like the dict returned
    by :meth:`VidTonePipeline.run` plus a ``video_id`` key injected by the
    batch runner.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=BATCH_CSV_FIELDS)
        writer.writeheader()
        for result in results:
            for row in _iter_rows(result):
                writer.writerow(row)
    return path
