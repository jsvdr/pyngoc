# Two stages: one resolves the dependencies with uv, the other only runs them.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
COPY README.md LICENSE ./
COPY src/ src/
COPY web/ web/

# --no-editable copies the package (and web/) into the virtual environment.
RUN uv sync --locked --no-dev --no-editable

# ---- runtime ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    HOST=0.0.0.0 \
    PORT=5000

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

EXPOSE 5000

# One worker with threads: the free instances have 512 MB and the workload is
# a few milliseconds of pure Python per request. Shell form so ${PORT} (set by
# the platform) is expanded; it falls back to 5000 locally.
CMD gunicorn "pyngo.app:app" --bind "0.0.0.0:${PORT:-5000}" --workers 1 --threads 4
