# Imagen de la API para Cloud Run (ADR-0002).
FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv

WORKDIR /app

# Dependencias primero, para aprovechar la caché de capas.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

ENV PATH="/opt/venv/bin:$PATH"

# Cloud Run indica el puerto en la variable PORT.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers"]
