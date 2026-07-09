from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency at runtime
    load_dotenv = None


TRUE_VALUES = {"1", "true", "yes", "y", "on"}


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


def _as_int(value: str | None, default: int) -> int:
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class AppConfig:
    use_mock: bool
    fireworks_api_key: str | None
    fireworks_model: str | None
    fireworks_vision_model: str | None
    fireworks_base_url: str
    max_retries: int
    min_video_seconds: int
    max_video_seconds: int
    output_dir: Path
    upload_dir: Path
    keyframe_interval_seconds: int
    max_keyframes: int
    max_vision_frames: int

    @classmethod
    def from_env(cls) -> "AppConfig":
        if load_dotenv is not None:
            load_dotenv()

        return cls(
            use_mock=_as_bool(os.getenv("USE_MOCK"), True),
            fireworks_api_key=os.getenv("FIREWORKS_API_KEY") or None,
            fireworks_model=os.getenv("FIREWORKS_MODEL") or None,
            fireworks_vision_model=os.getenv("FIREWORKS_VISION_MODEL") or None,
            fireworks_base_url=os.getenv(
                "FIREWORKS_BASE_URL",
                "https://api.fireworks.ai/inference/v1/chat/completions",
            ),
            max_retries=_as_int(os.getenv("MAX_RETRIES"), 2),
            min_video_seconds=_as_int(os.getenv("MIN_VIDEO_SECONDS"), 30),
            max_video_seconds=_as_int(os.getenv("MAX_VIDEO_SECONDS"), 120),
            output_dir=Path(os.getenv("OUTPUT_DIR", "outputs")),
            upload_dir=Path(os.getenv("UPLOAD_DIR", "uploads")),
            keyframe_interval_seconds=_as_int(os.getenv("KEYFRAME_INTERVAL_SECONDS"), 10),
            max_keyframes=_as_int(os.getenv("MAX_KEYFRAMES"), 8),
            max_vision_frames=_as_int(os.getenv("MAX_VISION_FRAMES"), 3),
        )

    @property
    def can_call_fireworks(self) -> bool:
        return bool(self.fireworks_api_key and self.fireworks_model and not self.use_mock)

    @property
    def can_call_vision(self) -> bool:
        # Vision uses the same API key. When no dedicated vision model is
        # configured we simply skip the vision step.
        return bool(
            self.fireworks_api_key
            and self.fireworks_vision_model
            and not self.use_mock
        )

    def ensure_dirs(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
