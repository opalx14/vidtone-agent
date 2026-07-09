# ---------- Stage 1: Build the React + Vite frontend with Bun ----------
FROM oven/bun:1.2-alpine AS web-builder

WORKDIR /web
COPY apps/web/package.json apps/web/bun.lock ./
RUN bun install --frozen-lockfile

COPY apps/web/ ./
RUN bun run build


# ---------- Stage 2: Python FastAPI backend + static SPA ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8710

WORKDIR /app

# System deps needed by OpenCV, MoviePy, and video I/O.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching.
COPY requirements.txt pyproject.toml README.md ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy the rest of the project.
COPY vidtone ./vidtone
COPY apps ./apps
COPY prompts ./prompts
COPY samples ./samples
COPY scripts ./scripts

# Install the local package so the `vidtone` CLI is available.
RUN pip install -e .

# Bring in the compiled frontend from the web-builder stage.
COPY --from=web-builder /web/dist ./apps/web/dist

# Create runtime folders that would otherwise be missing on a fresh container.
RUN mkdir -p outputs uploads

EXPOSE 8710

# Simple liveness probe against the FastAPI /health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:8710/health || exit 1

CMD ["python", "-m", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8710"]
