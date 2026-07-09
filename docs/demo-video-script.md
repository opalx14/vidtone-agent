# Demo Video Script — VidTone Agent

Target length: **2:30 – 3:00**. Hard cap: 5:00 per lablab.ai rules. Aspect
ratio: **16:9**. Format: **MP4**. Suggested resolution: 1920×1080 at 30
fps.

Structure follows the lablab.ai rulebook: introduce the problem, present
the solution, walk through the working demo, close with the differentiator
and links.

---

## Preflight checklist

Before you hit record:

- [ ] `.env` has `USE_MOCK=false`, a valid `FIREWORKS_API_KEY`, and a
      Gemma `FIREWORKS_MODEL`. Verify with the config sanity check in
      `docs/FIREWORKS_SETUP.md` §5a.
- [ ] `bun run build` in `apps/web/` succeeded (there is a `dist/`).
- [ ] Run `bun run dev` OR `docker compose up --build`. Confirm the UI
      opens at http://127.0.0.1:5179 (dev) or http://localhost:8710
      (Docker).
- [ ] `samples/vidtone_sample.mp4` exists (generate with
      `vidtone make-sample --output samples/vidtone_sample.mp4 --seconds 30 --fps 10`).
      Optionally add a second real short clip for variety.
- [ ] Close chat / notification apps. Silence your phone.
- [ ] Terminal font size ≥ 18pt so command output is legible.
- [ ] Use QuickTime, OBS, or Loom. Record system audio + microphone.

## Recording tools

- **QuickTime (macOS)** → File → New Screen Recording → select area.
- **OBS Studio** for pro output: one scene with a browser source + one
  scene with the terminal. Add a small webcam overlay if you want to be on
  camera in the intro.
- **Loom** → fast if you don't need editing.

---

## Timeline

### 0:00 – 0:20 · Intro (20 s)

Show slide 1 (the deck cover) as the first frame.

Voiceover:

> "Hi, I'm <name>. This is VidTone Agent, my submission for AMD Developer
> Hackathon Act-II, Track 2 — Video Captioning. It's a caption QA copilot
> for short-video teams."

### 0:20 – 0:45 · The problem (25 s)

Cut to slide 2. Read the three bullets quickly.

Voiceover:

> "Content teams need the same clip captioned five different ways for five
> different platforms. LLMs can help, but they hallucinate and drift off
> tone. Manual review does not scale. That's the pain we're solving."

### 0:45 – 1:05 · What it does + the differentiator (20 s)

Cut to slide 3, then slide 4.

Voiceover on slide 3:

> "VidTone Agent takes one short video, generates four required styles —
> formal, sarcastic, humorous-tech, humorous-non-tech — then hands each
> caption to a Judge Agent."

Voiceover on slide 4:

> "The Judge scores accuracy, tone, and hallucination on a 1 to 10 scale.
> Anything below threshold gets rewritten with the judge's notes as
> guidance. This Generate–Judge–Revise loop is the differentiator we want
> the LLM leaderboard to reward."

### 1:05 – 2:15 · Live demo (70 s)

Switch to a full-window screen capture of the running app.

Steps to hit on camera:

1. **(0:05)** Open the browser, refresh the app, show the empty UI with
   the hero copy and the "Mock mode" toggle.
2. **(0:10)** Click the upload area, pick `samples/vidtone_sample.mp4`.
   Confirm the preview player renders.
3. **(0:05)** Uncheck **Mock mode** so the request routes to Fireworks.
   Say out loud: "Turning off Mock mode routes everything through Gemma on
   Fireworks."
4. **(0:05)** Click **Generate captions**. Show the loading spinner.
5. **(0:20)** When results appear, hover the four caption cards. Read one
   card aloud, e.g.:

   > "Formal: <caption text>. Accuracy 9, Tone 8, Risk 2. That's the Judge
   > Agent talking — it scored this caption before shipping it."

6. **(0:10)** Point at the JSON download button, click it, and open the
   file briefly on-screen. Highlight:
   - `"mode": "fireworks"`
   - `"source": "fireworks"` inside a caption
   - the numeric scores
7. **(0:10)** Switch to the terminal window, run
   `python -m vidtone.interfaces.cli run samples/vidtone_sample.mp4 --real`
   as a side channel proof for judges who prefer CLI.
8. **(0:05)** Return to the browser.

Voiceover cue for the demo:

> "One upload, four captions, and every caption comes with a judge score
> before it leaves the app."

### 2:15 – 2:40 · Gemma + architecture (25 s)

Cut to slide 5, then slide 6.

Voiceover on slide 5:

> "The whole thing runs as a single Docker container on port 8710. React
> UI, FastAPI, and the AI pipeline live in one image."

Voiceover on slide 6:

> "Both the caption pass and the strict-JSON judge pass go through a Gemma
> model on Fireworks. That's how we're entering the Best Use of Gemma in
> Video Captioning partner prize."

### 2:40 – 3:00 · Close + roadmap (20 s)

Cut to slide 8 (roadmap + thanks). Then a final title card with the
Hugging Face Spaces URL and the GitHub repo URL.

Voiceover:

> "Vision on keyframes is already wired in as an optional pass. Next up:
> batch mode against the fixed hackathon set, Whisper transcripts, and a
> judge calibration report. Repo and live demo links are on screen.
> Thanks!"

---

## Editing hints

- Cut every long pause; keep the pace tight.
- Add small captions or lower-thirds over the terminal parts so viewers
  can read the exact commands.
- Zoom the mouse cursor when clicking small controls (the Mock toggle).
- Do a final full pass at 1.0× to check the audio is louder than any
  system beep or fan noise.

## Upload

1. Export as **MP4**, H.264 video, AAC audio, ≤ 5:00.
2. Upload as **Unlisted** on YouTube and paste the link into the lablab.ai
   form's *Video Presentation* field. (Uploading raw MP4 is also allowed
   by the platform but the URL flow is more reliable.)
3. If you prefer a hosted CDN, use Vimeo or a direct S3 link. Same
   requirement — the file must be publicly reachable by judges.
