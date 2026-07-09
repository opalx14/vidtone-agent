# Fireworks + Gemma Setup

Everything you need to switch VidTone Agent from mock mode to real Fireworks
inference. Do these steps once; the rest of the app reads `.env` on every
run.

## Prerequisites

- Fireworks coupon from AMD Developer Hackathon Act-II email (looks like
  `FW-LABLAB-XXXX`).
- A working `.venv` with `pip install -e .` completed (see the main README).
- `curl` available in a terminal for the smoke test.

---

## 1. Redeem the coupon

The coupon is **not** an API key. It funds your Fireworks account with
credits that API keys can then spend.

1. Sign in at <https://fireworks.ai>.
2. Open **Settings → Billing** (some accounts show it under **Credits**).
3. Paste the coupon code → **Apply**.
4. Confirm the credit shows up in your balance.

Do this **before** the coupon expires or gets used from a screenshot.

## 2. Create an API key

1. Open **Settings → API Keys** on the Fireworks console.
2. Click **Create API Key**. Name it something like `vidtone-hackathon`.
3. Copy the key — it starts with `fw_...` — and store it in a password
   manager. The full key is only shown once.

**Never** commit the key, paste it into chats, or screenshot it into
publicly shared images.

## 3. Pick a model slug

We verified two paths end-to-end:

**Default path — `gpt-oss-120b`** (recommended, tested on the coupon-tier
Fireworks account used for this build):

```text
accounts/fireworks/models/gpt-oss-120b
```

This is a strong OSS-based reasoning model. It returns clean
`content` + a separate `reasoning_content` field, which makes the strict
JSON judge output easy to parse. Verified with all four caption styles and
a stable Judge Agent pass in `outputs/real-single/vidtone_sample_vidtone.json`.

**Bonus path — Gemma via Fireworks** (if your account has access):

For the *Best Use of Gemma in Video Captioning* $3,000 partner prize, swap
in a Gemma model:

1. On <https://fireworks.ai>, open **Models**.
2. Filter by *Gemma*. If you see Gemma variants listed, copy the full slug
   (looks like `accounts/fireworks/models/gemma-3-27b-it`).
3. If Gemma is not listed for your account, you cannot target this prize
   — the coupon-tier account we tested with only exposed
   `gpt-oss-120b`, `kimi-k2p6`, `deepseek-v4-pro`, `glm-5p2`, and a few
   image models. Contact hackathon organizers in Discord if you believe
   Gemma should be enabled.

Do not retype the slug from memory; copy-paste from the model detail page.
A single wrong character produces a 404 at runtime.

## 4. Fill `.env`

From the repo root:

```bash
cp .env.example .env
```

Edit `.env` so it contains:

```env
USE_MOCK=false
FIREWORKS_API_KEY=fw_XXXXXXXXXXXXXXXXXXXX
FIREWORKS_MODEL=accounts/fireworks/models/gpt-oss-120b
FIREWORKS_BASE_URL=https://api.fireworks.ai/inference/v1/chat/completions
```

All other keys can stay at their defaults.

`.env` is already git-ignored, so it won't leak to GitHub.

If you obtained Gemma access, replace the `FIREWORKS_MODEL` line with the
Gemma slug you copied in §3.

## 5. Verify the wiring (three layers)

### 5a. Config sanity — free, ~1 second

```bash
source .venv/bin/activate
python -c "from vidtone.core.config import AppConfig; c=AppConfig.from_env(); print('can_call_fireworks =', c.can_call_fireworks, '| model =', c.fireworks_model)"
```

Expected:

```text
can_call_fireworks = True | model = accounts/fireworks/models/gpt-oss-120b
```

If it prints `False`, one of `USE_MOCK`, `FIREWORKS_API_KEY`, or
`FIREWORKS_MODEL` is wrong. Re-open `.env` and check for typos or missing
values.

### 5b. Raw curl — costs ~$0.001

Confirms the key and model slug are valid:

```bash
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)

curl -s https://api.fireworks.ai/inference/v1/chat/completions \
    -H "Authorization: Bearer $FIREWORKS_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"$FIREWORKS_MODEL\", \"messages\": [{\"role\":\"user\",\"content\":\"ping\"}], \"max_tokens\": 10}" \
    | python -m json.tool
```

- 200 with `choices[0].message.content` present → OK.
- 401 → API key wrong or coupon not redeemed.
- 404 → model slug wrong.
- 429 → rate limited; wait and retry.

### 5c. Full pipeline — costs ~$0.02–0.05 per run

```bash
vidtone make-sample --output samples/vidtone_sample.mp4 --seconds 30 --fps 10
vidtone run samples/vidtone_sample.mp4 --real --output-dir outputs
```

Open the generated JSON in `outputs/`. All four captions should have:

```json
{
  "source": "fireworks",
  "judge_source": "fireworks"
}
```

If any caption still shows `"source": "mock"`, the pipeline silently fell
back — usually because `USE_MOCK` is still `true` or the API key is empty.

## 6. Use the real mode in the web UI

1. Make sure `.env` has `USE_MOCK=false` and the two Fireworks values.
2. Start the app: `bun run dev` (or `docker compose up --build`).
3. Open the UI, upload a clip.
4. **Uncheck the *Mock mode* toggle** before clicking **Generate captions**.
5. Confirm the response header shows `Mode: fireworks` and the caption
   cards show `source: fireworks`.

## 7. Deploying with a Fireworks key

On Hugging Face Spaces (or any hosted platform):

- Do **not** upload `.env`.
- Add the two secrets `FIREWORKS_API_KEY` and `FIREWORKS_MODEL` in the
  platform's environment / secrets UI. VidTone reads them via `os.getenv`
  exactly the same way as local.
- Consider keeping `USE_MOCK=true` on public deployments if you do not want
  every visitor spending your credits. Then leave `USE_MOCK` unset (or
  `true`) in the Space and use the local Docker run for the real-mode
  demo recording.

## Troubleshooting

- **UI shows mock captions even after unchecking the toggle.** Restart the
  API — `.env` is read once at process start.
- **`OpenAI-compatible client returned 400`.** Some Fireworks models expect
  `max_tokens` to be small (< 512). VidTone already uses ≤ 240 for judge
  calls. Try a different Gemma variant.
- **Judge scores keep coming back with `source: "fallback-parser"`.** The
  model returned invalid JSON. Try a bigger Gemma variant, or edit
  `prompts/judge_prompts.py` to add a shorter example.

## What counts as "the Fireworks path is working"

For the hackathon leaderboard we need the JSON export to show, for every
style, this exact combination:

```json
{
  "source": "fireworks",
  "judge_source": "fireworks",
  "accuracy_score": <int 1..10>,
  "tone_score": <int 1..10>,
  "hallucination_risk": <int 1..10>,
  "notes": "..."
}
```

Anything else (`mock`, `fallback-parser`) means the real path did not fully
run.
