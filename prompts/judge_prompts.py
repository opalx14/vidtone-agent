from __future__ import annotations


def build_judge_prompt(style: str, video_context: str, caption: str) -> str:
    return f"""
You are the VidTone Judge Agent.

Evaluate the caption against the video context and requested style.

Requested style: {style}

Video context:
{video_context}

Caption:
{caption}

Score from 1 to 10 for:
- accuracy_score: how faithful the caption is to the video context
- tone_score: how clearly it matches the requested style
- hallucination_risk: 1 means low risk, 10 means high risk

Return strict JSON only:
{{
  "accuracy_score": 8,
  "tone_score": 8,
  "hallucination_risk": 2,
  "notes": "brief explanation"
}}
""".strip()
