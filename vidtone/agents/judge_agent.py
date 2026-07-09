from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from prompts.judge_prompts import build_judge_prompt
from vidtone.clients.fireworks_client import FireworksClient
from vidtone.core.config import AppConfig


@dataclass(frozen=True)
class JudgeResult:
    accuracy_score: int
    tone_score: int
    hallucination_risk: int
    notes: str
    source: str

    @property
    def needs_revision(self) -> bool:
        return self.accuracy_score < 7 or self.tone_score < 7 or self.hallucination_risk > 6

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class JudgeAgent:
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

    def judge(self, style: str, caption: str, video_context: str) -> JudgeResult:
        if self.client is None:
            return self._mock_judge(style, caption)

        prompt = build_judge_prompt(style, video_context, caption)
        raw = self.client.complete(
            prompt=prompt,
            system_prompt="You are a strict evaluator that returns valid JSON only.",
            temperature=0.0,
            max_tokens=900,
        )
        return self._parse_judge_json(raw)

    @staticmethod
    def _parse_judge_json(raw: str) -> JudgeResult:
        cleaned = raw.strip()

        # Strip triple-backtick code fences (```json ... ```).
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json\n", "", 1).replace("JSON\n", "", 1)

        # Some reasoning-style models add a short preamble before the JSON
        # body. Extract the first balanced {...} block so the parser is
        # resilient to that pattern.
        if not cleaned.lstrip().startswith("{"):
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                cleaned = cleaned[start : end + 1]

        try:
            data = json.loads(cleaned)
            return JudgeResult(
                accuracy_score=int(data.get("accuracy_score", 6)),
                tone_score=int(data.get("tone_score", 6)),
                hallucination_risk=int(data.get("hallucination_risk", 4)),
                notes=str(data.get("notes", "No notes returned.")),
                source="fireworks",
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return JudgeResult(
                accuracy_score=6,
                tone_score=6,
                hallucination_risk=5,
                notes=f"Judge output was not valid JSON: {raw[:200]}",
                source="fallback-parser",
            )

    @staticmethod
    def _mock_judge(style: str, caption: str) -> JudgeResult:
        base_tone = 8 if style.replace("_", " ") or caption else 7
        if style == "formal":
            tone = 8
        elif style == "sarcastic":
            tone = (
                8
                if any(word in caption.lower() for word in ["bravely", "apparently", "very"])
                else 7
            )
        elif style == "humorous_tech":
            tone = (
                9
                if any(word in caption.lower() for word in ["kubernetes", "stack", "pod"])
                else 7
            )
        else:
            tone = 8

        return JudgeResult(
            accuracy_score=8,
            tone_score=max(base_tone, tone),
            hallucination_risk=2,
            notes="Mock judge: caption is structurally valid for MVP demo. Use real mode for final scoring.",
            source="mock",
        )
