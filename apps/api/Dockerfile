FROM python:3.13-slim AS builder

WORKDIR /app

RUN pip install uv --no-cache-dir

# Copy workspace config first (layer caching)
COPY pyproject.toml .
COPY apps/api/pyproject.toml apps/api/
COPY packages/sdk/pyproject.toml packages/sdk/

# Copy source
COPY apps/api/runledger_api apps/api/runledger_api
COPY apps/api/alembic apps/api/alembic
COPY apps/api/alembic.ini apps/api/alembic.ini
COPY apps/api/scripts apps/api/scripts
COPY packages/sdk/runledger_sdk packages/sdk/runledger_sdk

# Install dependencies for runledger-api
RUN uv sync --package runledger-api --no-dev

# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.13-slim AS runtime

WORKDIR /app

# pg_dump / pg_restore for backups over the network (review P-21). PGDG's client 17 can
# dump any server up to 17; Debian's own client would be too old for a 16/17 server.
RUN apt-get update  && apt-get install -y --no-install-recommends ca-certificates curl gnupg  && install -d /usr/share/postgresql-common/pgdg  && curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc  && . /etc/os-release  && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" > /etc/apt/sources.list.d/pgdg.list  && apt-get update  && apt-get install -y --no-install-recommends postgresql-client-17  && apt-get purge -y --auto-remove gnupg  && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/apps/api/runledger_api /app/runledger_api
COPY --from=builder /app/apps/api/alembic /app/alembic
COPY --from=builder /app/apps/api/alembic.ini /app/alembic.ini
COPY --from=builder /app/apps/api/scripts /app/scripts

RUN sed -i 's/\r$//' /app/scripts/start.sh && chmod +x /app/scripts/start.sh

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Build identity (CI passes the release version and git sha). The system status page
# compares it across api, workers and beat to catch version skew (cd:S-06).
ARG RUNLEDGER_VERSION=0.1.0
ARG RUNLEDGER_BUILD_SHA=local
ENV RUNLEDGER_VERSION=${RUNLEDGER_VERSION} RUNLEDGER_BUILD_SHA=${RUNLEDGER_BUILD_SHA}
LABEL org.opencontainers.image.version=${RUNLEDGER_VERSION} org.opencontainers.image.revision=${RUNLEDGER_BUILD_SHA}

EXPOSE 8000

CMD ["/app/scripts/start.sh"]
