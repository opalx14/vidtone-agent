# Slide Deck Outline — VidTone Agent

Eight slides, 16:9. Design suggestion: dark theme, single accent color per
slide, keep text short so it reads well from a video recording. Export as
PDF for the lablab.ai submission and as PNG frames for reuse inside the
demo video.

Fonts that work fast: Inter or IBM Plex Sans for text, JetBrains Mono for
code. All can be swapped for Google-hosted defaults.

---

## Slide 1 — Title

**Headline:** VidTone Agent
**Sub-headline:** Caption QA Copilot for short-video teams

Bottom bar (small text):
- AMD Developer Hackathon: ACT II · Track 2 — Video Captioning
- Built with Fireworks AI + Gemma · MIT licensed
- Team / author name · date

**Speaker note:**
> Hi, I'm <name>. This is VidTone Agent, my submission for AMD Developer
> Hackathon Act-II Track 2: Video Captioning.

---

## Slide 2 — The problem

**Headline:** Short-video captioning is fast, but noisy

Three bullets:
- Creators need multiple tones per clip (formal, sarcastic, funny…)
- One-shot AI captions drift off context and hallucinate
- Manual review does not scale to a whole content team

**Speaker note:**
> Every social team writes the same clip five different ways for five
> different platforms. LLMs can help, but they hallucinate and miss tone.
> Manual review is slow. That's the pain we're solving.

---

## Slide 3 — What VidTone Agent does

**Headline:** One video → four caption styles → a self-check pass

Flow arrow diagram:

```text
video ─▶ metadata / keyframes ─▶ CaptionAgent
        └───────────────────────────────────▶ JudgeAgent
                                              └▶ revise if weak
                                              └▶ export JSON / CSV
```

Side callout: the four required styles — formal, sarcastic, humorous_tech,
humorous_non_tech.

**Speaker note:**
> Upload one clip. We extract metadata and keyframes, generate four caption
> styles, and then run every caption through a Judge Agent that scores it.

---

## Slide 4 — The differentiator: Generate → Judge → Revise

**Headline:** A second adversarial pass, not a single-shot caption

Two-column layout:

Left column — Judge scores every caption:
- accuracy_score (1–10)
- tone_score (1–10)
- hallucination_risk (1–10)
- structured notes

Right column — Auto revise when:
- accuracy < 7, or
- tone < 7, or
- hallucination_risk > 6

**Speaker note:**
> This is what we want the LLM judge to reward. Every caption is scored on
> three dimensions and rewritten if it fails any threshold. It's an
> agentic loop, not a prompt.

---

## Slide 5 — Architecture

**Headline:** Single Docker container, single port

Boxes / arrows:

- React + Vite + TypeScript SPA (Bun-built) → `/` and `/assets/*`
- FastAPI on `:8710` → `/health`, `/api/caption`, `/api/export`
- VidTonePipeline (Python) → VisionAgent → CaptionAgent → JudgeAgent
- Fireworks AI (Gemma text) + Fireworks AI (vision, optional)
- JSON + CSV exporter → `outputs/`

Corner label:
- Runs as one container on port 8710. Deployed on Hugging Face Spaces via
  the Docker SDK.

**Speaker note:**
> One Docker image serves the React UI, the FastAPI backend, and the AI
> pipeline. Fireworks does the heavy lifting for language and, optionally,
> vision.

---

## Slide 6 — Fireworks-powered, Gemma-ready

**Headline:** Both passes on Fireworks, Gemma-swappable for the partner prize

Bullets:
- Caption prompts → Fireworks (verified with `gpt-oss-120b`)
- Judge prompts → same Fireworks model, strict-JSON output
- Optional vision keyframe pass → Fireworks vision model
- One API key, one budget line, one deploy secret
- Swap `FIREWORKS_MODEL` to a Gemma slug when your account has access
  to unlock the *Best Use of Gemma in Video Captioning* $3,000 prize

Footer note:
- Reference build uses `gpt-oss-120b` because Gemma was not enabled on
  the tested coupon-tier account. Architecture is model-agnostic.

**Speaker note:**
> We route both the generation and the evaluation to a Fireworks model.
> Our reference runs use gpt-oss-120b, and the same code becomes
> Gemma-powered by flipping one env var — which is our entry point to the
> Best Use of Gemma in Video Captioning partner prize.

---

## Slide 7 — Live demo screenshot / QR

**Headline:** Try it live

Left: hero screenshot of the UI showing four caption cards with score
badges (accuracy / tone / risk) and the JSON/CSV export buttons.

Right column:
- Public app URL (Hugging Face Spaces)
- GitHub repo URL
- QR code that opens the Space

**Speaker note:**
> Here's the app running end to end. Judges can click the QR code, upload a
> clip, and get four scored captions back in a minute.

---

## Slide 8 — Roadmap + thanks

**Headline:** What we ship next

Three columns:

Next 24 hours:
- Vision keyframe description enabled by default
- Batch mode against the fixed hackathon clip set

Next week:
- Whisper transcript for audio-heavy videos
- Judge calibration set + regression report

Longer term:
- Custom fine-tuned Gemma captioner
- Slack + Notion integrations for content teams

Bottom bar:
- Thanks to AMD, Fireworks AI, Google DeepMind (Gemma), lablab.ai
- Contact: <email or GitHub handle>

**Speaker note:**
> Vision on keyframes goes on by default next. Then Whisper transcripts and
> a calibration set for the judge. Thanks to AMD, Fireworks, Google
> DeepMind, and lablab.ai for the event.

---

## Export instructions

1. Create the deck in Google Slides, Keynote, or Figma.
2. Match the outline above; keep to 8 slides.
3. Export **File → Download → PDF Document (.pdf)** at 16:9.
4. Save to `docs/assets/vidtone-slides.pdf`.
5. Upload the PDF in the *Slide Presentation* field of the lablab.ai form.
