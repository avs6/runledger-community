FROM python:3.13-slim AS builder

WORKDIR /app

RUN pip install uv --no-cache-dir

# Copy workspace config first (layer caching)
COPY pyproject.toml .
COPY apps/api/pyproject.toml apps/api/
COPY packages/sdk/pyproject.toml packages/sdk/

# Copy source
COPY apps/api/runledger_api apps/api/runledger_api
COPY packages/sdk/runledger_sdk packages/sdk/runledger_sdk

# Install dependencies for runledger-api
RUN uv sync --package runledger-api --no-dev

# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.13-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/apps/api/runledger_api /app/runledger_api

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

EXPOSE 8000

CMD ["uvicorn", "runledger_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
