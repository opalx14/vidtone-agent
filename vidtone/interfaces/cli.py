from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from vidtone.core.batch import run_batch
from vidtone.core.config import AppConfig
from vidtone.core.pipeline import VidTonePipeline
from vidtone.core.segments import run_segmented_video
from vidtone.processing.video_processor import read_video_metadata


def _apply_common_env(args: argparse.Namespace) -> None:
    if getattr(args, "mock", False):
        os.environ["USE_MOCK"] = "true"
    if getattr(args, "real", False):
        os.environ["USE_MOCK"] = "false"
    for env_name, arg_name in [
        ("OUTPUT_DIR", "output_dir"),
        ("UPLOAD_DIR", "upload_dir"),
        ("FIREWORKS_API_KEY", "api_key"),
        ("FIREWORKS_MODEL", "model"),
        ("FIREWORKS_VISION_MODEL", "vision_model"),
    ]:
        value = getattr(args, arg_name, None)
        if value:
            os.environ[env_name] = value


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    # Segmented runs produce a different top-level shape (see
    # vidtone/core/segments.py::run_segmented_video). Detect it and render a
    # summary that actually surfaces segment counts instead of empty fields.
    if result.get("segmented"):
        return {
            "segmented": True,
            "source_video": result.get("source_video"),
            "mode": result.get("mode"),
            "model": result.get("model"),
            "total": result.get("total"),
            "succeeded": result.get("succeeded"),
            "failed": result.get("failed"),
            "exports": result.get("exports", {}),
        }
    captions = result.get("captions", {})
    return {
        "mode": result.get("mode"),
        "video": result.get("video", {}).get("filename"),
        "duration_seconds": result.get("video", {}).get("duration_seconds"),
        "caption_styles": list(captions.keys()),
        "exports": result.get("exports", {}),
        "warnings": result.get("warnings", []),
    }


def _print_result(result: dict[str, Any], full_json: bool) -> None:
    print(json.dumps(result if full_json else _summary(result), indent=2, ensure_ascii=False))


def run_command(args: argparse.Namespace) -> int:
    _apply_common_env(args)
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Video not found: {video_path}", file=sys.stderr)
        return 2

    config = AppConfig.from_env()

    # Optional long-video auto-segmentation (P1). We only segment when the
    # user explicitly passes --auto-segment AND the source video is longer
    # than the configured max_video_seconds. Short videos always fall back
    # to the verified single-pipeline path to avoid destabilizing Track 2.
    if getattr(args, "auto_segment", False):
        try:
            metadata = read_video_metadata(video_path)
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        duration = metadata.duration_seconds

        if duration is not None and duration > config.max_video_seconds:
            segment_seconds = min(max(30, int(args.segment_seconds)), 120)
            max_workers = min(max(1, int(args.max_workers)), 3)

            base_output = Path(args.output_dir) if args.output_dir else Path(
                "outputs/long-video"
            )
            stem = video_path.stem or "vidtone_long_video"
            segmented_output = base_output / stem

            result = run_segmented_video(
                config,
                video_path,
                segmented_output,
                segment_seconds=segment_seconds,
                max_workers=max_workers,
            )
            _print_result(result, args.full_json)
            total = int(result.get("total", 0) or 0)
            succeeded = int(result.get("succeeded", 0) or 0)
            # Non-zero exit only when we tried to process segments and every
            # one failed, matching batch_command's semantics.
            if total > 0 and succeeded == 0:
                return 1
            return 0

    result = VidTonePipeline(config).run(video_path)
    _print_result(result, args.full_json)
    return 0


def batch_command(args: argparse.Namespace) -> int:
    _apply_common_env(args)

    folder = Path(args.folder)
    if not folder.exists():
        print(f"Batch folder not found: {folder}", file=sys.stderr)
        return 2
    if not folder.is_dir():
        print(f"Batch path is not a directory: {folder}", file=sys.stderr)
        return 2

    output_dir = Path(args.output)

    # Parse the optional extensions list from `--extensions .mp4,.mov`.
    extensions = None
    if args.extensions:
        extensions = [
            (ext if ext.startswith(".") else f".{ext}").lower()
            for ext in args.extensions.split(",")
            if ext.strip()
        ]

    try:
        outcome = run_batch(
            AppConfig.from_env(),
            folder=folder,
            output_dir=output_dir,
            write_per_video=not args.no_per_video,
            extensions=extensions,
        )
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    manifest = outcome["manifest"]
    exports = outcome["exports"]

    summary = {
        "mode": manifest.get("mode"),
        "folder": manifest.get("folder"),
        "output_dir": manifest.get("output_dir"),
        "total": manifest.get("total"),
        "succeeded": manifest.get("succeeded"),
        "failed": manifest.get("failed"),
        "skipped": manifest.get("skipped"),
        "exports": exports,
    }
    if args.full_json:
        print(json.dumps(outcome, indent=2, ensure_ascii=False, default=str))
    else:
        print(json.dumps(summary, indent=2, ensure_ascii=False))

    # Non-zero exit when everything failed, so CI/judging scripts can catch it.
    if manifest.get("total", 0) > 0 and manifest.get("succeeded", 0) == 0:
        return 1
    return 0


def _create_test_video(video_path: Path, seconds: int = 2, fps: int = 10) -> None:
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Install requirements before creating test videos.") from exc

    video_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (320, 240))
    if not writer.isOpened():
        raise RuntimeError("Could not create test video.")

    for index in range(seconds * fps):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        frame[:, :, 0] = (index * 11) % 255
        frame[:, :, 1] = (index * 17) % 255
        frame[:, :, 2] = (index * 23) % 255
        cv2.putText(frame, f"VidTone {index + 1}", (36, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        writer.write(frame)
    writer.release()


def make_sample_command(args: argparse.Namespace) -> int:
    output_path = Path(args.output)
    _create_test_video(output_path, seconds=args.seconds, fps=args.fps)
    print(str(output_path))
    return 0


def smoke_test_command(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="vidtone-cli-") as temp_dir:
        temp_path = Path(temp_dir)
        video_path = temp_path / "smoke_test.mp4"
        os.environ["USE_MOCK"] = "true"
        os.environ["OUTPUT_DIR"] = str(temp_path / "outputs")
        os.environ["UPLOAD_DIR"] = str(temp_path / "uploads")
        _create_test_video(video_path, seconds=args.seconds, fps=args.fps)
        result = VidTonePipeline(AppConfig.from_env()).run(video_path)
        if len(result.get("captions", {})) != 4:
            print("Smoke test failed: expected four captions.", file=sys.stderr)
            return 1
        print("VidTone CLI smoke test passed.")
        _print_result(result, args.full_json)
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vidtone")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the pipeline on a single video.")
    run_parser.add_argument("video")
    run_parser.add_argument("--output-dir", default=None)
    run_parser.add_argument("--upload-dir", default=None)
    run_parser.add_argument("--api-key", default=None)
    run_parser.add_argument("--model", default=None)
    run_parser.add_argument("--vision-model", default=None)
    run_parser.add_argument("--mock", action="store_true")
    run_parser.add_argument("--real", action="store_true")
    run_parser.add_argument("--full-json", action="store_true")
    # P1 auto-segmentation opt-in (defaults off — Track 2 short-video flow
    # remains the verified default path).
    run_parser.add_argument(
        "--auto-segment",
        action="store_true",
        help=(
            "Split videos longer than MAX_VIDEO_SECONDS into chunks and "
            "run the pipeline on each chunk."
        ),
    )
    run_parser.add_argument(
        "--segment-seconds",
        type=int,
        default=60,
        help="Chunk length in seconds when --auto-segment is set (clamped to 30-120).",
    )
    run_parser.add_argument(
        "--max-workers",
        type=int,
        default=2,
        help="Concurrent segment workers when --auto-segment is set (clamped to 1-3).",
    )
    run_parser.set_defaults(func=run_command)

    batch_parser = subparsers.add_parser(
        "batch",
        help="Run the pipeline on every video in a folder (Track 2 flow).",
    )
    batch_parser.add_argument("folder", help="Folder containing videos.")
    batch_parser.add_argument(
        "--output",
        "-o",
        default="outputs/batch",
        help="Batch output directory (default: outputs/batch).",
    )
    batch_parser.add_argument("--api-key", default=None)
    batch_parser.add_argument("--model", default=None)
    batch_parser.add_argument("--vision-model", default=None)
    batch_parser.add_argument("--mock", action="store_true")
    batch_parser.add_argument("--real", action="store_true")
    batch_parser.add_argument(
        "--no-per-video",
        action="store_true",
        help="Skip writing per_video/<video_id>.json summaries.",
    )
    batch_parser.add_argument(
        "--extensions",
        default=None,
        help="Comma-separated list of file extensions to include, e.g. '.mp4,.mov'.",
    )
    batch_parser.add_argument("--full-json", action="store_true")
    batch_parser.set_defaults(func=batch_command)

    smoke_parser = subparsers.add_parser("smoke-test")
    smoke_parser.add_argument("--seconds", type=int, default=2)
    smoke_parser.add_argument("--fps", type=int, default=10)
    smoke_parser.add_argument("--full-json", action="store_true")
    smoke_parser.set_defaults(func=smoke_test_command)

    sample_parser = subparsers.add_parser("make-sample")
    sample_parser.add_argument("--output", default="samples/vidtone_sample.mp4")
    sample_parser.add_argument("--seconds", type=int, default=30)
    sample_parser.add_argument("--fps", type=int, default=10)
    sample_parser.set_defaults(func=make_sample_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "mock", False) and getattr(args, "real", False):
        print("Use only one of --mock or --real.", file=sys.stderr)
        return 2
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
