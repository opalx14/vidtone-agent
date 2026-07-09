# Submission Content — copy/paste into the lablab.ai form

Every block below is the exact text to paste into the corresponding field of
the AMD Developer Hackathon Act-II submission form on lablab.ai.

---

## Project Title

```
VidTone Agent
```

## Short Description (~140 chars)

```
Caption QA Copilot for short-video teams. Generates four caption styles, then a Judge Agent scores accuracy, tone, and hallucination.
```

Character count: ~140. Safe for platforms that cap the tagline at 160.

## Long Description (~1400 chars, safely within 600–2000)

```
VidTone Agent is a caption QA copilot for short-video teams. Built for AMD Developer Hackathon Act-II Track 2 (Video Captioning), it turns one short clip into four platform-ready caption styles: formal, sarcastic, humorous-tech, and humorous-non-tech.

Most captioning tools stop after generation. VidTone Agent adds a second, adversarial pass: a Judge Agent scores every caption on accuracy, tone match, and hallucination risk on a 1–10 scale. Weak captions (accuracy < 7, tone < 7, or hallucination > 6) are automatically rewritten with the judge's notes as guidance and re-scored. The full Generate → Judge → Revise loop is what we want the LLM leaderboard to reward.

The pipeline runs on Fireworks AI. We verified end-to-end runs against gpt-oss-120b for both the caption pass and the strict-JSON judge pass. The FIREWORKS_MODEL env var can be swapped for any model your Fireworks account exposes; if Gemma is available, VidTone Agent routes both passes through it and becomes eligible for the Best Use of Gemma in Video Captioning partner prize. An optional Fireworks vision model can describe extracted keyframes, so the caption prompt is grounded in real visual content instead of only metadata.

The product ships as a single Docker container on port 8710 that serves both the FastAPI backend and a React + Vite + TypeScript SPA. Judges can inspect four caption cards with score badges, download JSON and CSV exports of every run, and toggle between mock and real Fireworks mode from the UI. A CLI (vidtone) supports scripted, headless runs, including a Track-2 style batch command that iterates a folder of clips and emits an aggregate CSV, JSON, and manifest.

Stack: Python 3.11, FastAPI, React + Vite + TypeScript, Bun, OpenCV, Fireworks AI. MIT licensed, deployed on Hugging Face Spaces.
```

Character count: ~1,880. Well within the 600–2,000 window most lablab.ai
forms accept.

## Technology and Category Tags

Pick 5–8 tags from what the form offers. Suggested set (adjust to what the
form actually shows):

```
Video Captioning
AI Agents
Fireworks AI
LLM-as-a-Judge
Python
FastAPI
React
TypeScript
Docker
```

If your Fireworks account exposes Gemma models and you swap `FIREWORKS_MODEL`
to a Gemma slug, add `Gemma` as an extra tag to signal the Gemma bonus track.

## Pitch one-liner (for social posts / demo intro)

```
Turn one short video into platform-ready captions, then let the Judge Agent score accuracy, tone, and hallucination risk.
```

## Speaker intro (2 sentences, for the demo video opener)

```
Hi, I'm building VidTone Agent for AMD Developer Hackathon Act-II Track 2. It's a caption QA copilot: it turns one short video into four different caption styles, then a Judge Agent scores each one for accuracy, tone, and hallucination risk before shipping.
```

## Team / Author line

Fill this in on the form itself; the platform pulls it from your lablab.ai
profile. Nothing to paste here.

## Public GitHub link

Paste your public repo URL, for example:

```
https://github.com/<your-username>/vidtone-agent
```

Make sure the repo is set to **Public**, the README renders correctly, and
`.env` is **not** committed.

## Application URL

After deploying to Hugging Face Spaces (see `docs/FIREWORKS_SETUP.md` and
the README quick-start), paste the Space URL:

```
https://huggingface.co/spaces/<your-username>/vidtone-agent
```

If the deploy takes longer than expected, the fallback message for the
Application URL field is the Docker one-liner:

```
docker compose up --build → http://localhost:8710
```
