from __future__ import annotations

from vidtone.clients.fireworks_client import FireworksClient, FireworksClientError
from vidtone.core.config import AppConfig


_VISION_PROMPT = """
Describe what is visually happening across the following keyframes of a
short video. Return 2-4 short sentences that together capture:

- The main subjects visible in the frames
- The setting or scene
- Any noticeable action or camera motion between frames
- Any on-screen text you can read confidently

Do not invent anything you cannot see. If the frames look abstract or
uninformative, say so briefly instead of guessing.
""".strip()


class VisionAgent:
    """Small helper that summarizes extracted keyframes with a vision-capable
    Fireworks model.

    When the config does not enable vision (`use_mock=true`, no API key, or
    no `FIREWORKS_VISION_MODEL` set), `describe()` returns an empty string
    and the pipeline falls back to metadata-only context.
    """

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.client = self._build_client()

    def _build_client(self) -> FireworksClient | None:
        if not self.config.can_call_vision:
            return None
        return FireworksClient(
            api_key=self.config.fireworks_api_key or "",
            model=self.config.fireworks_vision_model or "",
            base_url=self.config.fireworks_base_url,
        )

    def describe(self, keyframe_paths: list[str]) -> str:
        if self.client is None or not keyframe_paths:
            return ""

        # Send only the first N frames to keep token spend and latency low.
        limit = max(1, self.config.max_vision_frames)
        frames_for_prompt = keyframe_paths[:limit]

        try:
            description = self.client.complete_multimodal(
                prompt=_VISION_PROMPT,
                image_paths=frames_for_prompt,
            )
        except FireworksClientError:
            # Vision is a best-effort enhancement. Never fail the pipeline
            # if the vision call errors out.
            return ""

        return description.strip()
