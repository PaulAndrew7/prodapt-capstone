# Clause API image. Build context is the repository root (see compose.yaml) so the demo
# corpus in data/demo can be seeded from inside the container.
FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/var/lib/clause/models/huggingface \
    HF_HUB_DISABLE_TELEMETRY=1

WORKDIR /srv/services/api
COPY services/api/pyproject.toml services/api/uv.lock services/api/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY services/api/alembic.ini ./
COPY services/api/migrations ./migrations
COPY services/api/app ./app
COPY data/demo /srv/data/demo

RUN useradd --system --uid 10001 clause \
    && mkdir -p /var/lib/clause/storage /var/lib/clause/models \
    && chown -R clause /var/lib/clause
USER clause

EXPOSE 8000
# Migrations are an explicit step: docker compose run --rm api python -m app.cli migrate
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
