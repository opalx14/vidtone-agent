from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from vidtone.agents.caption_agent import CAPTION_STYLES, CaptionAgent
from vidtone.agents.judge_agent import JudgeAgent
from vidtone.agents.vision_agent import VisionAgent
from vidtone.core.config import AppConfig
from vidtone.processing.video_processor import (
    build_video_context,
    extract_keyframes,
    read_video_metadata,
    validate_video_duration,
)
from vidtone.storage.exporter import write_csv, write_json


class VidTonePipeline:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.config.ensure_dirs()
        self.caption_agent = CaptionAgent(config)
        self.judge_agent = JudgeAgent(config)
        self.vision_agent = VisionAgent(config)

    def run(self, video_path: str | Path) -> dict[str, Any]:
        video_path = Path(video_path)
        metadata = read_video_metadata(video_path)
        warnings = validate_video_duration(
            metadata,
            min_seconds=self.config.min_video_seconds,
            max_seconds=self.config.max_video_seconds,
        )
        keyframes = extract_keyframes(
            video_path,
            self.config.output_dir,
            every_seconds=self.config.keyframe_interval_seconds,
            max_frames=self.config.max_keyframes,
        )

        # Vision pass: describe the top keyframes if a vision model is
        # configured. Returns "" when vision is disabled or the call fails,
        # so build_video_context safely degrades to metadata-only context.
        visual_notes = self.vision_agent.describe(keyframes)
        vision_source = "fireworks" if visual_notes else "skipped"

        video_context = build_video_context(
            metadata,
            keyframes,
            visual_notes=visual_notes,
        )

        captions: dict[str, Any] = {}
        for style in CAPTION_STYLES:
            first_caption = self.caption_agent.generate(style, video_context)
            first_judge = self.judge_agent.judge(style, first_caption.text, video_context)
            needs_revision = first_judge.needs_revision

            if needs_revision:
                revised_caption = self.caption_agent.revise(
                    style=style,
                    video_context=video_context,
                    previous_caption=first_caption.text,
                    judge_notes=first_judge.notes,
                )
                revised_judge = self.judge_agent.judge(
                    style, revised_caption.text, video_context
                )
                final_caption = revised_caption
                final_judge = revised_judge
            else:
                final_caption = first_caption
                final_judge = first_judge

            captions[style] = {
                # Final caption after possible revision.
                "text": final_caption.text,
                "source": final_caption.source,
                # Final judge scores that ship in the export.
                "accuracy_score": final_judge.accuracy_score,
                "tone_score": final_judge.tone_score,
                "hallucination_risk": final_judge.hallucination_risk,
                "notes": final_judge.notes,
                "judge_source": final_judge.source,
                # Revision provenance: True when the first-pass caption was
                # below the judge's threshold and was rewritten.
                "needs_revision": needs_revision,
                "original_caption": first_caption.text if needs_revision else None,
                "original_accuracy_score": first_judge.accuracy_score if needs_revision else None,
                "original_tone_score": first_judge.tone_score if needs_revision else None,
                "original_hallucination_risk": first_judge.hallucination_risk if needs_revision else None,
            }

        result: dict[str, Any] = {
            "project": "VidTone Agent",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "mock" if not self.config.can_call_fireworks else "fireworks",
            "video": metadata.to_dict(),
            "warnings": warnings,
            "keyframes": keyframes,
            "visual_notes": visual_notes,
            "vision_source": vision_source,
            "video_context": video_context,
            "captions": captions,
        }

        stem = video_path.stem or "vidtone_result"
        json_path = write_json(result, self.config.output_dir / f"{stem}_vidtone.json")
        csv_path = write_csv(result, self.config.output_dir / f"{stem}_vidtone.csv")
        result["exports"] = {
            "json": str(json_path),
            "csv": str(csv_path),
        }
        write_json(result, json_path)
        return result
