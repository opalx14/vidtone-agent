from __future__ import annotations

STYLE_GUIDE = {
    "formal": "Professional, concise, neutral, suitable for a business report.",
    "sarcastic": "Witty and dry, but not rude, offensive, or inaccurate.",
    "humorous_tech": "Funny for a technical audience, with light software/AI metaphors.",
    "humorous_non_tech": "Funny for a general audience, simple and accessible.",
}


def build_caption_prompt(style: str, video_context: str) -> str:
    guide = STYLE_GUIDE[style]
    return f"""
You are VidTone Agent, a multi-style video captioning assistant.

Task:
Generate one short caption or summary for the video in the requested style.

Style: {style}
Style guide: {guide}

Rules:
- Stay faithful to the video context.
- Do not invent people, brands, places, dialogue, or events not supported by the context.
- Keep it to 1-2 sentences.
- Make the tone obvious but still accurate.
- Return only the caption text, no markdown.

Video context:
{video_context}
""".strip()


def build_revision_prompt(
    style: str,
    video_context: str,
    previous_caption: str,
    judge_notes: str,
) -> str:
    guide = STYLE_GUIDE[style]
    return f"""
Revise the caption so it scores higher for accuracy and style.

Style: {style}
Style guide: {guide}

Previous caption:
{previous_caption}

Judge notes:
{judge_notes}

Video context:
{video_context}

Return only the revised caption text, no markdown.
""".strip()
