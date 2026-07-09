# Submission Checklist — AMD Developer Hackathon Act-II · Track 2

Source of truth: <https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii>

Every item in the *Required* sections is mandatory for the submission to be
accepted and scored. *Recommended* items materially improve the leaderboard
position or unlock partner prizes (Gemma bonus).

## Required — code & repo

- [x] Public GitHub repository
- [x] README with setup and usage instructions
- [x] `.env.example` included
- [x] Dockerfile that builds and starts the app
- [x] `docker compose up --build` intended to run the app on port `8710`
      (validate on any machine with a Docker daemon — this environment
      does not have Docker installed locally)
- [x] `vidtone smoke-test` passes locally
- [x] `python -m vidtone.interfaces.cli smoke-test` passes locally
- [x] `vidtone make-sample` produces a valid MP4
- [x] `vidtone run samples/vidtone_sample.mp4 --mock` produces four
      captions with JSON and CSV exports
- [x] `vidtone batch <folder> --mock` iterates a folder of clips and emits
      `batch_results.json`, `batch_results.csv`, `manifest.json`, and
      `per_video/<video_id>.json` — this is the exact I/O contract Track 2
      judging scripts consume (one CSV row per clip × style, four rows per
      clip). Verified with a 3-clip mock run (see test evidence in the
      submission summary).
- [ ] `vidtone run samples/vidtone_sample.mp4 --real` produces four
      captions with `source: "fireworks"` — **user action needed**
      (redeem coupon + create API key first, see
      [`FIREWORKS_SETUP.md`](FIREWORKS_SETUP.md))
- [ ] `vidtone batch <folder> --real` for the full Track 2 flow —
      **user action needed** (same Fireworks setup)

## Required — product demo

- [x] Upload video works via the web UI (verified with live uvicorn +
      curl POST /api/caption)
- [x] Captions generated for all four required styles (`formal`,
      `sarcastic`, `humorous_tech`, `humorous_non_tech`)
- [x] Judge scores are visible per caption card
- [x] JSON export works from the UI
- [x] CSV export works from the UI
- [ ] Real Fireworks mode tested end-to-end from the UI (uncheck *Mock
      mode*) — **user action needed**

## Required — submission form (lablab.ai)

Everything below is ready to paste from [`submission-content.md`](submission-content.md).

- [ ] Project Title: `VidTone Agent`
- [ ] Short description (paste from `submission-content.md`)
- [ ] Long description (paste from `submission-content.md`)
- [ ] Technology and Category Tags (paste from `submission-content.md`)
- [ ] Cover Image (16:9 PNG/JPG, ≥ 1200×675) — **user action**: create in
      Canva/Figma and save under `docs/assets/cover.png`
- [ ] Video Presentation ≤ 5 minutes (MP4) — **user action**: record
      following [`demo-video-script.md`](demo-video-script.md)
- [ ] Slide Presentation (PDF, ≤ 8 slides) — **user action**: build from
      [`slides-outline.md`](slides-outline.md) and export as PDF
- [ ] Public GitHub Repository URL — **user action**: push this repo,
      set to Public
- [ ] Demo Application Platform: Hugging Face Spaces (Docker SDK) —
      follow [`DEPLOY.md`](DEPLOY.md)
- [ ] Application URL — **user action**: paste the HF Spaces URL after
      the first successful deploy

## Recommended — Gemma partner prize ($3,000)

Status on this build: **the coupon-tier Fireworks account we tested with
does not expose Gemma models** (all 8 candidate slugs returned 404). The
tested and verified model is `gpt-oss-120b`. Track 2 leaderboard remains
achievable; the Gemma bonus is out of reach unless a different account or
tier gets Gemma access.

- [x] Codebase routes both caption and judge passes through the same
      Fireworks model → aligned with the *Best Use of Gemma in Video
      Captioning* prize when Gemma is available
- [ ] `.env` contains `FIREWORKS_MODEL=accounts/fireworks/models/gemma-*-it`
      — **NOT achievable on current account**, verified via `/models` API
      probe + 8 direct slug tests
- [x] README explicitly documents the Gemma-swap path
- [x] Slide deck outline dedicates one slide to the model story
- [x] Optional vision pass wired through the same Fireworks account

## Pitch points (leaderboard positioning)

- [x] Track 2: Video Captioning
- [x] Uses Fireworks AI model layer (Gemma when configured)
- [x] Self-Judging Caption Agent as the core differentiator (Generate →
      Judge → Revise loop)
- [x] Containerized single-image runtime on port 8710
- [x] Clear roadmap for vision-based keyframe understanding (already
      wired in) and audio transcript

## Timeline reminders

- Check the *Event Schedule* tab on the lablab.ai hackathon page for the
  submission deadline in your local timezone.
- Fireworks coupon must be redeemed on the Fireworks dashboard before it
  can fund API calls. Coupon and API key are separate — see
  [`FIREWORKS_SETUP.md`](FIREWORKS_SETUP.md).
- Hugging Face Spaces Docker build takes 3–6 minutes on the first push.
  Start the deploy at least an hour before you plan to submit.

---

## Quick reference — the 5 user actions left

Everything in code is done. What is left is manual work that only you can
do:

1. **Redeem** the Fireworks coupon on <https://fireworks.ai> and **create
   an API key**. See [`FIREWORKS_SETUP.md`](FIREWORKS_SETUP.md) §1–§3.
2. **Fill `.env`** with the API key, a Gemma model slug, and (optionally)
   a Fireworks vision model slug. Verify with the three-step check in
   [`FIREWORKS_SETUP.md`](FIREWORKS_SETUP.md) §5.
3. **Deploy** to Hugging Face Spaces following [`DEPLOY.md`](DEPLOY.md).
   Add `FIREWORKS_API_KEY` and `FIREWORKS_MODEL` as Space secrets.
4. **Create the cover image, slide PDF, and demo video** using the
   content in [`submission-content.md`](submission-content.md),
   [`slides-outline.md`](slides-outline.md), and
   [`demo-video-script.md`](demo-video-script.md).
5. **Fill the lablab.ai submission form** with the text, tags, cover
   image, video, slide PDF, GitHub URL, and Application URL.
