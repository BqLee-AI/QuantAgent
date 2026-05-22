FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/README.md ./apps/api/
COPY packages/core/pyproject.toml ./packages/core/

RUN uv sync --locked --no-dev --no-editable --no-install-workspace --package quantagent-api --package quantagent-core

COPY apps/api/src ./apps/api/src
COPY packages/core/src ./packages/core/src
COPY packages/core/alembic.ini ./packages/core/alembic.ini
COPY packages/core/alembic ./packages/core/alembic

RUN uv sync --locked --no-dev --no-editable --package quantagent-api --package quantagent-core

FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

ENV PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production \
    HOST=0.0.0.0 \
    PORT=8000 \
    PYTHONUNBUFFERED=1

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/packages/core/alembic.ini /app/packages/core/alembic.ini
COPY --from=builder /app/packages/core/alembic /app/packages/core/alembic
COPY plugins ./plugins

RUN useradd --create-home --shell /usr/sbin/nologin quantagent \
    && mkdir -p /app/runtime \
    && chown -R quantagent:quantagent /app

USER quantagent

EXPOSE 8000

CMD ["api"]
