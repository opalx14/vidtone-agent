# Deploying VidTone Agent to Hugging Face Spaces

The hackathon submission form requires an *Application URL*. Hugging Face
Spaces is the fastest free option that also supports the exact Docker image
we already ship. Everything below assumes you have a Hugging Face account
and can push to a Space.

## What the Space will look like

- SDK: **Docker**
- Port: **8710** (matches `Dockerfile` and `docker-compose.yml`)
- Build source: this repository, via git push
- Two secrets: `FIREWORKS_API_KEY` and `FIREWORKS_MODEL` (optional
  `FIREWORKS_VISION_MODEL`)
- `USE_MOCK` left as `true` by default so random visitors don't burn
  through your Fireworks credits

## One-time setup

1. Go to <https://huggingface.co/spaces> → **Create new Space**.
2. Fill the form:
   - **Owner**: your username or an org you belong to.
   - **Space name**: `vidtone-agent` (matches `title` in the README front
     matter).
   - **License**: `mit`.
   - **Space SDK**: **Docker** → **Blank**.
   - **Hardware**: **CPU basic (free)** is fine for a captioning demo.
     Fireworks does the heavy work; the Space only needs to run FastAPI
     and serve the SPA.
   - **Visibility**: **Public**.
3. Click **Create Space**. HF will scaffold an empty repo.

## First deploy from your local repo

The README front matter (`title`, `sdk`, `app_port`, …) is already Spaces
compatible. All you need to do is push this repo as the Space's git remote.

```bash
# Add the Space as a second remote (once).
git remote add space https://huggingface.co/spaces/<username>/vidtone-agent

# Push.
git push space HEAD:main
```

If the Space rejects the push because the branch is different, run
`git push space main` explicitly, or force-push the first time only:
`git push -f space main`.

The Space UI will show a **Building** state; the two-stage Dockerfile
takes 3–6 minutes on the first build.

Once the build finishes, the URL is:

```text
https://huggingface.co/spaces/<username>/vidtone-agent
```

That is the value to paste into the submission form's **Application URL**
field.

## Add the Fireworks secrets

On the Space page:

1. Open **Settings** (top right).
2. Scroll to **Repository secrets** → **New secret**.
3. Add:
   - `FIREWORKS_API_KEY` = `fw_...` (from Fireworks console)
   - `FIREWORKS_MODEL` = `accounts/fireworks/models/gemma-3-27b-it`
   - `FIREWORKS_VISION_MODEL` (optional) = a Fireworks vision model slug
4. **Do not** add `USE_MOCK`. Leave it unset on the Space (defaults to
   `true`) so drive-by traffic uses mock mode. Judges who want to try real
   mode just uncheck the *Mock mode* toggle in the UI, and the request
   carries `use_mock=false` — but the API still needs the API key you
   just set to reach Fireworks.

Restart the Space (**Settings → Restart Space**) so the new environment is
picked up.

## Verifying the live Space

Once the status turns **Running**:

```bash
curl https://<username>-vidtone-agent.hf.space/health
```

Expected JSON:

```json
{"ok": true, "service": "vidtone-api", "api_port": 8710, "web_port": 5179, "mode": "mock-ready"}
```

`mock-ready` is fine here — it means the API keys are wired but the
default request is still `use_mock=true` unless the caller says otherwise.

Then open the URL in a browser, upload a short clip, and confirm four
caption cards render.

## Common failure modes

- **Build hangs on `bun install`.** Bun on Alpine can be slow. Give it up
  to 10 minutes on a first cold build.
- **Build fails with `apps/web/bun.lock` not found.** The lockfile is
  checked into git in this repo. If you regenerated `bun.lock` locally,
  commit the new file before pushing.
- **App is up but the UI is 404.** Check that `apps/web/dist/index.html`
  was actually built during the first Docker stage. The `web-builder`
  stage in the Dockerfile runs `bun run build`; the second stage copies
  `dist/`. If your fork changed folder names, adjust both stages.
- **Fireworks 401 in the Space but works locally.** The secret was set
  before the Space was restarted. Restart the Space and try again.

## Updating the Space later

Every push to the `space/main` branch triggers a rebuild:

```bash
git push space HEAD:main
```

If you want to publish only a specific commit:

```bash
git push space <sha>:main
```

## Fallback plan (no deploy)

If you cannot deploy in time, submit the Docker one-liner as the
Application URL note:

```text
docker compose up --build  →  http://localhost:8710
```

Judges accept this per the "runnable using provided instructions" rule,
but a live URL always plays better on the leaderboard.
