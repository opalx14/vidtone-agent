# VidTone Agent Enhancement Spec: Model Selector + Long Video Segmentation

## Context

Project: `vidtone-agent`

Current verified state:

- Track: AMD Developer Hackathon Act-II — Track 2 Video Captioning.
- Core flow already works: video → context/keyframes → Caption Agent → Judge Agent → revise if weak → JSON/CSV export.
- Single-video real mode has passed with Fireworks.
- Batch real mode has passed with Fireworks.
- Verified model: `accounts/fireworks/models/gpt-oss-120b`.
- Gemma is not currently available on the account, so the project should not claim Gemma usage or Gemma bonus unless it is actually verified later.
- `.env` is ignored and must never be committed.

Current gaps before final polish:

1. Users cannot choose the Fireworks model from the Web UI.
2. Long videos only produce a duration warning; they are not automatically split into short captionable segments.

The goal of this spec is to add the smallest useful enhancement set without destabilizing the already-working submission flow.

---

## Guiding Principle

Do not break the verified short-video Track 2 flow.

Existing behavior must keep working:

```text
short video 30–120s
→ generate 4 caption styles
→ judge accuracy/tone/hallucination
→ revise if needed
→ export JSON/CSV
```

Enhancements should be opt-in where risky:

- Model selection: safe to expose by default.
- Long-video segmentation: opt-in only, not enabled by default.

---

## Priority

### P0 — Must do if there is time before final submit

Add model selector / model override.

Why:

- Makes the product more flexible.
- Lets judges/users swap Fireworks models depending on account access.
- Aligns with reality: verified model is `gpt-oss-120b`, but other Fireworks models can be configured.
- Low risk because CLI already supports `--model`.

### P1 — Nice to have if P0 is stable

Add optional long-video segmentation.

Why:

- Current app only warns for videos > 120s.
- Real users may upload longer videos.
- Segmenting long videos into short chunks makes the tool more practical.

Do not block submission on P1 if time is short.

---

# P0: Fireworks Model Selector / Override

## Product Behavior

The app should allow users to choose which Fireworks model to use for caption generation and judging.

Default model:

```text
accounts/fireworks/models/gpt-oss-120b
```

Suggested preset models:

```text
accounts/fireworks/models/gpt-oss-120b
accounts/fireworks/models/gpt-oss-20b
custom
```

The custom option should allow users to paste any Fireworks model slug available to their account.

The UI should make clear:

```text
Model access depends on your Fireworks account.
```

## Backend API Changes

File:

```text
apps/api/main.py
```

Current endpoint:

```python
@app.post("/api/caption")
async def caption_video(
    video: UploadFile = File(...),
    use_mock: bool = Form(False),
) -> dict[str, object]:
```

Add optional form field:

```python
model: str | None = Form(None)
```

Update config builder from:

```python
def _build_request_config(use_mock: bool) -> AppConfig:
    base_config = AppConfig.from_env()
    if use_mock:
        return replace(base_config, use_mock=True)
    return replace(base_config, use_mock=False)
```

To behavior equivalent to:

```python
def _build_request_config(use_mock: bool, model: str | None = None) -> AppConfig:
    base_config = AppConfig.from_env()
    selected_model = model.strip() if model and model.strip() else base_config.fireworks_model
    return replace(
        base_config,
        use_mock=bool(use_mock),
        fireworks_model=selected_model,
    )
```

Acceptance:

- If model is not provided, current `.env` model is used.
- If model is provided, request uses that model.
- If use_mock=true, still returns mock result and should not call Fireworks.
- API response includes the selected model somewhere obvious.

Recommended response field:

```json
{
  "model": "accounts/fireworks/models/gpt-oss-120b"
}
```

This can be added in `VidTonePipeline.run()` result using `self.config.fireworks_model`.

## Pipeline Result Changes

File:

```text
vidtone/core/pipeline.py
```

Add to result:

```python
"model": self.config.fireworks_model,
"vision_model": self.config.fireworks_vision_model,
```

This helps demo and debugging.

Batch manifest should also include model.

File:

```text
vidtone/core/batch.py
```

Add to manifest:

```python
"model": config.fireworks_model,
"vision_model": config.fireworks_vision_model,
```

## Frontend Changes

File:

```text
apps/web/src/main.tsx
```

Add state:

```tsx
const DEFAULT_MODEL = 'accounts/fireworks/models/gpt-oss-120b';
const [modelPreset, setModelPreset] = React.useState(DEFAULT_MODEL);
const [customModel, setCustomModel] = React.useState('');
```

Model resolution:

```tsx
const selectedModel = modelPreset === 'custom' ? customModel.trim() : modelPreset;
```

When submitting form:

```tsx
if (selectedModel) {
  formData.append('model', selectedModel);
}
```

UI controls:

```text
Model
[ dropdown: gpt-oss-120b / gpt-oss-20b / custom ]
[ custom input shown only when custom selected ]
```

Result header should show:

```text
Mode: fireworks · Model: accounts/fireworks/models/gpt-oss-120b
```

Acceptance:

- Default UI runs real mode with `gpt-oss-120b` when Mock mode is off.
- User can choose `gpt-oss-20b` or paste a custom model slug.
- If model is unavailable, backend returns a clear Fireworks error through current error handling.
- Mock mode still works.

## CLI Verification

CLI already supports:

```bash
python -m vidtone.interfaces.cli run samples/vidtone_sample.mp4 \
  --real \
  --model accounts/fireworks/models/gpt-oss-120b \
  --output-dir /tmp/vidtone-model-test
```

Test this explicitly and verify summary includes:

```text
mode: fireworks
caption_styles: 4 styles
warnings: []
```

---

# P1: Optional Long-Video Auto Segmentation

## Product Behavior

If a user uploads a video longer than `MAX_VIDEO_SECONDS` and enables auto segmentation:

```text
long video
→ split into fixed-length segments
→ run existing pipeline on each segment
→ export aggregate segment JSON/CSV
```

Default:

```text
auto_segment=false
```

Recommended defaults:

```text
segment_seconds=60
max_workers=2
```

Do not segment by default. For hackathon Track 2, short video behavior is still primary.

## UX Behavior

Frontend should expose:

```text
[ ] Auto segment long videos
Segment length: 60 seconds
Max workers: 2
```

Only enable these fields when auto segment is checked.

Result should show:

```text
Long video: segmented
Segments: N
```

If auto_segment=false and video is long, keep current warning behavior.

## Segment Runner Design

Add new module:

```text
vidtone/core/segments.py
```

Responsibilities:

1. Read metadata.
2. If duration <= max_video_seconds, return normal pipeline result or signal no segmentation needed.
3. If duration > max_video_seconds, split into segments.
4. Run `VidTonePipeline` on each segment.
5. Export aggregate JSON/CSV.
6. Return a result object compatible enough for API/CLI display.

Suggested functions:

```python
def split_video(
    video_path: Path,
    output_dir: Path,
    segment_seconds: int = 60,
) -> list[dict[str, Any]]:
    ...


def run_segmented_video(
    config: AppConfig,
    video_path: Path,
    output_dir: Path,
    segment_seconds: int = 60,
    max_workers: int = 2,
) -> dict[str, Any]:
    ...
```

Segment metadata shape:

```json
{
  "segment_id": "segment_001",
  "path": "outputs/segments/segment_001.mp4",
  "start_seconds": 0,
  "end_seconds": 60,
  "duration_seconds": 60
}
```

## Splitting Implementation

Use OpenCV if available, because the project already depends on OpenCV.

Basic approach:

- Open source video with `cv2.VideoCapture`.
- Read FPS, width, height, frame count.
- Calculate segment frame ranges.
- Write each segment with `cv2.VideoWriter`.

Fallback:

- If video unreadable or metadata unavailable, raise a clear error.

No ffmpeg dependency should be added unless already present.

## Concurrency

Use `concurrent.futures.ThreadPoolExecutor` with safe default:

```python
max_workers = min(max(1, max_workers), 3)
```

Reason:

- Fireworks API/rate limits can fail if too many calls are made.
- Each segment creates multiple model calls: 4 caption calls + 4 judge calls + possible revision calls.

Recommended default:

```text
2 workers
```

Failure isolation:

- If one segment fails, record it in manifest.
- Continue processing other segments.
- Return non-zero CLI exit only if all segments fail.

## Output Structure

For long video:

```text
outputs/long-video/<video_stem>/
├── manifest.json
├── segment_results.json
├── segment_results.csv
├── segments/
│   ├── segment_001.mp4
│   ├── segment_002.mp4
│   └── ...
└── per_segment/
    ├── segment_001.json
    ├── segment_002.json
    └── ...
```

CSV fields:

```text
source_video
segment_id
start_seconds
end_seconds
segment_duration_seconds
mode
model
style
caption
accuracy_score
tone_score
hallucination_risk
judge_notes
needs_revision
original_caption
final_caption
```

## API Changes for P1

File:

```text
apps/api/main.py
```

Add form fields:

```python
auto_segment: bool = Form(False)
segment_seconds: int = Form(60)
max_workers: int = Form(2)
```

Behavior:

```python
if auto_segment and uploaded_duration > config.max_video_seconds:
    result = run_segmented_video(...)
else:
    result = VidTonePipeline(config).run(video_path)
```

Important:

- Do not segment short videos.
- Do not segment when auto_segment=false.
- Clamp segment_seconds to a safe range, e.g. 30–120.
- Clamp max_workers to 1–3.

## CLI Changes for P1

File:

```text
vidtone/interfaces/cli.py
```

Add to `run` command:

```bash
--auto-segment
--segment-seconds 60
--max-workers 2
```

Example:

```bash
python -m vidtone.interfaces.cli run long_video.mp4 \
  --real \
  --auto-segment \
  --segment-seconds 60 \
  --max-workers 2 \
  --output-dir outputs/long-video-test
```

Optional for batch command:

```bash
python -m vidtone.interfaces.cli batch clips \
  --real \
  --auto-segment \
  --segment-seconds 60 \
  --max-workers 2 \
  --output outputs/batch-segmented
```

If time is short, implement P1 for single-video `run` and Web API first. Batch integration can be a follow-up.

---

# Tests / Verification

## Before changing code

Confirm current baseline still passes:

```bash
source .venv/bin/activate
python -m vidtone.interfaces.cli run samples/vidtone_sample.mp4 \
  --real \
  --output-dir /tmp/vidtone-baseline-real
```

Expected:

```text
mode: fireworks
duration_seconds: 30.0
caption_styles: 4
warnings: []
```

## P0 Tests

### CLI model override

```bash
python -m vidtone.interfaces.cli run samples/vidtone_sample.mp4 \
  --real \
  --model accounts/fireworks/models/gpt-oss-120b \
  --output-dir /tmp/vidtone-model-real
```

Expected:

```text
mode: fireworks
caption_styles: 4
warnings: []
```

### API model override

Run API then POST multipart with:

```text
video=@samples/vidtone_sample.mp4
use_mock=false
model=accounts/fireworks/models/gpt-oss-120b
```

Expected:

```text
mode: fireworks
model: accounts/fireworks/models/gpt-oss-120b
captions: 4 styles
```

### Web model selector

Manual test:

1. Open web.
2. Upload `samples/vidtone_sample.mp4`.
3. Mock mode off.
4. Select `gpt-oss-120b`.
5. Generate.
6. Verify result header shows mode + model.

## P1 Tests

### Create long sample

```bash
python -m vidtone.interfaces.cli make-sample \
  --output /tmp/vidtone_long_150s.mp4 \
  --seconds 150 \
  --fps 10
```

### Without auto segment

```bash
python -m vidtone.interfaces.cli run /tmp/vidtone_long_150s.mp4 \
  --mock \
  --output-dir /tmp/vidtone-long-warning
```

Expected:

```text
warning: above target range of 30-120s
no segmentation
```

### With auto segment

```bash
python -m vidtone.interfaces.cli run /tmp/vidtone_long_150s.mp4 \
  --mock \
  --auto-segment \
  --segment-seconds 60 \
  --max-workers 2 \
  --output-dir /tmp/vidtone-long-segmented
```

Expected:

```text
segmented: true
segments: 3
failed: 0
segment_results.csv exists
segment_results.json exists
```

Use mock first for P1. Only run real segmentation after mock passes, because real mode can spend credits quickly.

### Real long-video test

Only run with a small 130–150s test video and max_workers=1 or 2.

```bash
python -m vidtone.interfaces.cli run /tmp/vidtone_long_150s.mp4 \
  --real \
  --auto-segment \
  --segment-seconds 60 \
  --max-workers 1 \
  --output-dir /tmp/vidtone-long-segmented-real
```

Expected:

```text
mode: fireworks
segments >= 2
some succeeded
CSV exists
```

---

# Documentation Updates

Update:

```text
README.md
.env.example
docs/FIREWORKS_SETUP.md
docs/submission-checklist.md
docs/demo-video-script.md
```

Add:

```text
Model selection:
- Default verified model is accounts/fireworks/models/gpt-oss-120b.
- Users can override the Fireworks model in CLI, API, or Web UI.
- Gemma can be swapped in if the account has access, but it is not claimed as the verified default.

Long video handling:
- Track 2 targets 30–120s videos.
- Longer videos produce warnings by default.
- Optional auto-segmentation can split long videos into 60s chunks for caption QA.
```

---

# Risk Controls

Do not commit:

```text
.env
outputs/* runtime files
samples/*.mp4
uploads/*
__pycache__
*.egg-info
```

Before commit:

```bash
git status
git ls-files | grep -E '(^\.env$|outputs/|samples/.*\.(mp4|mov|webm)$|uploads/|__pycache__|egg-info)' || true
```

Should show no sensitive/runtime files except allowed `.gitkeep` files.

Do not claim:

```text
Best Use of Gemma
Using Gemma
Gemma bonus
```

unless Gemma real mode actually passes.

---

# Final Recommendation

If submit deadline is close:

```text
Implement P0 only.
Do not implement P1 before submission.
```

If there is enough time and P0 is stable:

```text
Implement P1 with mock tests first, then one small real test.
```

For the hackathon demo, the safest story remains:

```text
VidTone Agent is a Caption QA Copilot for short-video teams.
It generates four platform-ready caption styles, judges accuracy/tone/hallucination risk, revises weak captions, and exports JSON/CSV for a full batch of videos.
```
