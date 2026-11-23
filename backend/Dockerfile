# syntax=docker/dockerfile:1
# api / worker / scheduler / migrate で共通のイメージ（ADR 0035）。起動のコマンドは compose で変える。
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 依存だけ先に入れる（コードの変更でキャッシュが無効にならないように）
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev

RUN useradd --system --uid 10001 --home-dir /app app
USER app

EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --retries=10 \
  CMD ["python", "-c", "import urllib.request as u; u.urlopen(u.Request('http://127.0.0.1:8000/healthz', headers={'X-Healthcheck': '1'}), timeout=2)"]
CMD ["uvicorn", "thinkronos.bootstrap:create_api", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
