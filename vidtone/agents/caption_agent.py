from __future__ import annotations

from dataclasses import asdict, dataclass

from prompts.caption_prompts import build_caption_prompt, build_revision_prompt
from vidtone.clients.fireworks_client import FireworksClient
from vidtone.core.config import AppConfig


CAPTION_STYLES = [
    "formal",
    "sarcastic",
    "humorous_tech",
    "humorous_non_tech",
]


@dataclass(frozen=True)
class CaptionResult:
    style: str
    text: str
    source: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class CaptionAgent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.client = self._build_client()

    def _build_client(self) -> FireworksClient | None:
        if not self.config.can_call_fireworks:
            return None
        return FireworksClient(
            api_key=self.config.fireworks_api_key or "",
            model=self.config.fireworks_model or "",
            base_url=self.config.fireworks_base_url,
        )

    def generate(self, style: str, video_context: str) -> CaptionResult:
        if style not in CAPTION_STYLES:
            raise ValueError(f"Unsupported style: {style}")

        if self.client is None:
            return CaptionResult(
                style=style,
                text=self._mock_caption(style, video_context),
                source="mock",
            )

        prompt = build_caption_prompt(style, video_context)
        caption = self.client.complete(
            prompt=prompt,
            system_prompt="You generate accurate short captions for video content.",
            temperature=0.5,
            max_tokens=800,
        )
        return CaptionResult(style=style, text=caption, source="fireworks")

    def revise(
        self,
        style: str,
        video_context: str,
        previous_caption: str,
        judge_notes: str,
    ) -> CaptionResult:
        if self.client is None:
            return CaptionResult(
                style=style,
                text=self._mock_caption(style, video_context, revised=True),
                source="mock-revision",
            )

        prompt = build_revision_prompt(style, video_context, previous_caption, judge_notes)
        caption = self.client.complete(
            prompt=prompt,
            system_prompt="You revise captions to improve accuracy and requested tone.",
            temperature=0.45,
            max_tokens=800,
        )
        return CaptionResult(style=style, text=caption, source="fireworks-revision")

    @staticmethod
    def _mock_caption(style: str, video_context: str, revised: bool = False) -> str:
        label = "Revised mock" if revised else "Mock"
        snippets = {
            "formal": "A concise overview of the uploaded video is generated from its metadata and visual context.",
            "sarcastic": "Another video bravely enters the AI pipeline and emerges with a caption that sounds very intentional.",
            "humorous_tech": "The clip gets routed through the caption stack like a tiny Kubernetes pod looking for meaning.",
            "humorous_non_tech": "This video walked into the app, and the app politely tried to explain what just happened.",
        }
        context_hint = video_context.splitlines()[0].replace("Video file: ", "") if video_context else "video"
        return f"{label}: {snippets[style]} ({context_hint})"
