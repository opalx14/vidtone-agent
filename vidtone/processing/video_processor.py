from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VideoMetadata:
    path: str
    filename: str
    size_bytes: int
    duration_seconds: float | None
    fps: float | None
    frame_count: int | None
    width: int | None
    height: int | None
    readable: bool
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_import_cv2():
    try:
        import cv2  # type: ignore

        return cv2
    except ImportError:
        return None


def read_video_metadata(video_path: str | Path) -> VideoMetadata:
    path = Path(video_path)
    warnings: list[str] = []

    if not path.exists():
        raise FileNotFoundError(f"Video not found: {path}")

    cv2 = _safe_import_cv2()
    if cv2 is None:
        warnings.append("OpenCV is not installed, so only basic file metadata is available.")
        return VideoMetadata(
            path=str(path),
            filename=path.name,
            size_bytes=path.stat().st_size,
            duration_seconds=None,
            fps=None,
            frame_count=None,
            width=None,
            height=None,
            readable=False,
            warnings=warnings,
        )

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        warnings.append("OpenCV could not open this video file.")
        return VideoMetadata(
            path=str(path),
            filename=path.name,
            size_bytes=path.stat().st_size,
            duration_seconds=None,
            fps=None,
            frame_count=None,
            width=None,
            height=None,
            readable=False,
            warnings=warnings,
        )

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    capture.release()

    duration = frame_count / fps if fps > 0 and frame_count > 0 else None
    if duration is None:
        warnings.append("Could not determine video duration.")

    return VideoMetadata(
        path=str(path),
        filename=path.name,
        size_bytes=path.stat().st_size,
        duration_seconds=round(duration, 2) if duration is not None else None,
        fps=round(fps, 2) if fps > 0 else None,
        frame_count=frame_count or None,
        width=width or None,
        height=height or None,
        readable=True,
        warnings=warnings,
    )


def validate_video_duration(
    metadata: VideoMetadata,
    min_seconds: int,
    max_seconds: int,
) -> list[str]:
    warnings = list(metadata.warnings)
    duration = metadata.duration_seconds

    if duration is None:
        warnings.append("Duration is unknown; hackathon range validation was skipped.")
        return warnings

    if duration < min_seconds:
        warnings.append(
            f"Video is {duration}s, below the target range of {min_seconds}-{max_seconds}s."
        )
    elif duration > max_seconds:
        warnings.append(
            f"Video is {duration}s, above the target range of {min_seconds}-{max_seconds}s."
        )

    return warnings


def extract_keyframes(
    video_path: str | Path,
    output_dir: str | Path,
    every_seconds: int = 10,
    max_frames: int = 8,
) -> list[str]:
    cv2 = _safe_import_cv2()
    if cv2 is None:
        return []

    path = Path(video_path)
    frame_dir = Path(output_dir) / f"{path.stem}_keyframes"
    frame_dir.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return []

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if fps <= 0 or frame_count <= 0:
        capture.release()
        return []

    step = max(1, int(fps * max(1, every_seconds)))
    candidate_indices = list(range(0, frame_count, step))[:max_frames]
    if not candidate_indices:
        candidate_indices = [0]

    saved_paths: list[str] = []
    for index in candidate_indices:
        capture.set(cv2.CAP_PROP_POS_FRAMES, index)
        success, frame = capture.read()
        if not success:
            continue
        timestamp = index / fps
        filename = f"frame_{math.floor(timestamp):04d}s.jpg"
        output_path = frame_dir / filename
        cv2.imwrite(str(output_path), frame)
        saved_paths.append(str(output_path))

    capture.release()
    return saved_paths


def build_video_context(
    metadata: VideoMetadata,
    keyframes: list[str],
    visual_notes: str = "",
) -> str:
    duration = metadata.duration_seconds
    duration_text = f"{duration} seconds" if duration is not None else "unknown duration"
    resolution = (
        f"{metadata.width}x{metadata.height}"
        if metadata.width is not None and metadata.height is not None
        else "unknown resolution"
    )
    keyframe_text = (
        f"{len(keyframes)} keyframes were extracted for visual inspection."
        if keyframes
        else "No keyframes were extracted."
    )

    visual_block = (
        f"Visual description: {visual_notes.strip()}"
        if visual_notes and visual_notes.strip()
        else "Visual description: Not available. Rely on metadata and filename hints."
    )

    return (
        f"Video file: {metadata.filename}\n"
        f"Duration: {duration_text}\n"
        f"Resolution: {resolution}\n"
        f"FPS: {metadata.fps or 'unknown'}\n"
        f"Visual notes: {keyframe_text}\n"
        f"{visual_block}\n"
        "Transcript: Not available in MVP yet. Use filename, metadata, and extracted frames as context."
    )
