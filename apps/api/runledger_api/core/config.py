import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://runledger:runledger@localhost:5432/runledger"

    # Redis (also used as Celery broker/backend)
    redis_url: str = "redis://localhost:6379/0"
    redis_appendonly: bool = False
    redis_appendfsync: str = "everysec"
    redis_snapshot_save: str = "900 1 300 10 60 10000"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    # Admin secret for /admin/* endpoints.  If empty, falls back to secret_key.
    admin_secret: str = ""
    # Shared token the optimization microservices (memory, knowledge graph, skills,
    # semantic cache, context compiler, ...) require on every non-health request.
    # Falls back to ADMIN_SECRET, matching the docker-compose default.
    internal_service_token: str = ""
    # Shared secret used to verify HMAC-signed webhook ingest payloads.
    ingest_signing_secret: str = ""
    # Pepper for API key HMAC hashing (falls back to secret_key if empty).
    api_key_pepper: str = ""
    # Fernet key for encrypting ledger signing keys at rest.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ledger_master_key: str = ""
    # Comma-separated list of trusted reverse-proxy IPs for X-Forwarded-For validation.
    trusted_proxies: str = ""

    # App
    # Production validation is on by default (review P-14): a deployment that forgets
    # ENVIRONMENT gets the strict checks below, not dev mode. Local development and the
    # test suite set ENVIRONMENT=development explicitly.
    environment: str = "production"
    # Escape hatch for throwaway demo stacks only: start in production mode even though
    # known-default secrets are in use (each problem is still logged as a warning).
    allow_insecure_defaults: bool = False
    log_level: str = "INFO"
    runledger_mode: str = "community"
    # Build identity, baked into images by CI (RUNLEDGER_VERSION / RUNLEDGER_BUILD_SHA).
    # The system status page compares it across api, workers and beat (cd:S-06).
    runledger_version: str = "0.1.0"
    runledger_build_sha: str = "dev"
    # Dev-only demo admin (review P-01). Seeded only when ENVIRONMENT=development and
    # SEED_DEV_ADMIN is true; never in production, where /admin/bootstrap or the
    # dashboard's /setup page creates the first platform admin instead.
    seed_dev_admin: bool = True

    # CORS — comma-separated list of allowed origins.
    # In production set CORS_ORIGINS=https://your-frontend.railway.app
    # Dev defaults cover the dashboard (3201) on both localhost and 127.0.0.1 —
    # a browser Origin that isn't listed fails preflight
    # (400) and the dashboard shows "Failed to load …" on client-fetched pages.
    cors_origins: str = "http://localhost:3201,http://127.0.0.1:3201"

    # Provider pricing YAML file.  Mounted into the container by docker-compose.
    # Set PRICING_FILE=/path/to/pricing.yml to override.
    pricing_file: str = "/app/config/pricing.yml"

    # Email — disabled by default for local/demo stacks until SMTP is configured.
    email_enabled: bool = False
    email_reports_enabled: bool = False
    smtp_host: str = "smtp-relay.brevo.com"
    smtp_port: int = 587
    smtp_user: str = ""  # Brevo login email
    smtp_password: str = ""  # Brevo SMTP key
    smtp_from: str = "runledger@gmail.com"
    app_base_url: str = "http://localhost:3201"  # used for verification links
    platform_webhook_url: str = ""
    platform_slack_webhook_url: str = ""
    platform_webhook_events: str = "budget.breach,runaway.detected,backup.failed,backup.completed"

    # Backup/restore — product-managed scheduler is opt-in while S3 setup matures.
    backup_enabled: bool = False
    backup_command: str = ""
    backup_target: str = ""
    backup_timeout_seconds: int = 1800
    runledger_localai_s3_bucket: str = "runledger-backups"
    runledger_backup_endpoint_url: str = ""
    runledger_backup_region: str = "us-east-1"
    object_lifecycle_enabled: bool = False
    object_lifecycle_days: int = 90
    object_lifecycle_noncurrent_days: int = 30
    compliance_export_enabled: bool = False
    compliance_export_bucket: str = ""
    compliance_export_prefix: str = "compliance-exports"
    compliance_export_storage_class: str = "STANDARD_IA"
    compliance_export_retention_days: int = 365

    # Infra controls. (FEATURE_FLAGS was display-only and has been removed, review P-11.)
    abuse_protection_enabled: bool = True
    infra_policy_enforcement_mode: str = "advisory"
    deployment_profile: str = "core"
    local_tls_enabled: bool = False

    # ── Identity & sessions ───────────────────────────────────────────────────
    # Dashboard session keys expire after this many days (NextAuth maxAge matches).
    session_ttl_days: int = 7
    # Failed password/LDAP logins allowed per email (and per client IP) inside the
    # window before further attempts are rejected with 429.
    login_max_failures_per_account: int = 10
    login_max_failures_per_ip: int = 50
    login_failure_window_seconds: int = 900
    password_min_length: int = 12
    # Lifetime of SSO state (state + nonce + PKCE verifier) held in Redis.
    auth_state_ttl_seconds: int = 600
    # Verification / password-reset link lifetimes.
    email_verify_ttl_hours: int = 24
    password_reset_ttl_minutes: int = 60

    # ── Budgets ───────────────────────────────────────────────────────────────
    # Requests per minute the gateway still admits for a budget whose action is
    # "throttle" once it has reached its limit.
    budget_throttle_rpm: int = 10

    # ── Operational metrics ───────────────────────────────────────────────────
    metrics_token: str = ""
    # /health reports "degraded" (503) when beat stops sending heartbeats. Turn off
    # only for deployments that intentionally run without Celery beat.
    health_require_beat: bool = True
    ingest_rate_limit_per_minute: int = 10000

    # ── Ingestion ─────────────────────────────────────────────────────────────
    # Max events in one /ingest/v1/batch request, and max request body for ingest
    # and OTLP routes (compressed size as sent).
    ingest_max_batch_events: int = 1000
    ingest_max_body_bytes: int = 10 * 1024 * 1024
    # Max size an OTLP gzip body may inflate to (protects against gzip bombs).
    otlp_max_decompressed_bytes: int = 50 * 1024 * 1024
    # "llm": only traces with an LLM / agent / tool span become runs (others are
    # counted as dropped). "all": every trace becomes a run. A resource attribute
    # runledger.capture=all forces capture for one source.
    otlp_run_gating: str = "llm"
    # Days to keep raw OTLP data (batch payloads, raw spans, metrics/log batches)
    # and Kafka delivery rows. 0 keeps them forever.
    otlp_raw_retention_days: int = 14
    # Daily OTLP metric rollups are small; keep ~13 months for year-over-year views.
    otlp_metric_retention_days: int = 395
    # OTLP runs with no span activity for this long are closed as cancelled.
    otlp_inactivity_timeout_minutes: int = 15

    # ── Outbound destinations (webhooks, Slack, Kafka) ────────────────────────
    # Tenant-configured destinations may not resolve to private/internal addresses
    # unless the host is listed here (comma-separated) or private egress is allowed.
    egress_private_allowlist: str = "runledger-redpanda"
    egress_allow_private: bool = False
    # Gateway routes (review S-02): environment variables a route may name as its
    # provider key (globs), and extra hosts a route may send server-side keys to.
    provider_key_env_allowlist: str = "*_API_KEY,*_PROXY_KEY,*_SERVICE_ACCOUNT_JSON"
    gateway_base_url_allowlist: str = ""
    # Signed ingest: max clock skew, and how long a nonce is remembered.
    ingest_signature_tolerance_seconds: int = 300
    # Sliding-window limits per API key id (or client IP when unauthenticated), review
    # P-17. On by default; 0 disables a tier.
    analytics_rate_limit_per_minute: int = 1200
    management_rate_limit_per_minute: int = 600
    system_rate_limit_per_minute: int = 600

    # ── Celery (review P-12) ──────────────────────────────────────────────────
    # Per-task limits: soft raises SoftTimeLimitExceeded inside the task, hard kills
    # the worker child. Long-running maintenance tasks override these per task.
    celery_task_soft_time_limit: int = 300
    celery_task_time_limit: int = 360
    # Redis broker: a task not acked within this many seconds is redelivered. Must
    # exceed the longest task's hard limit (backups: backup_timeout_seconds).
    celery_visibility_timeout: int = 7200
    celery_worker_max_tasks_per_child: int = 500

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def effective_admin_secret(self) -> str:
        """Returns ADMIN_SECRET if set, otherwise falls back to SECRET_KEY."""
        return self.admin_secret or self.secret_key

    @property
    def internal_service_headers(self) -> dict[str, str]:
        """Headers for calls from the API/workers to internal optimization services."""
        return {"x-internal-token": self.internal_service_token or self.effective_admin_secret}

    @property
    def effective_ingest_signing_secret(self) -> str:
        """Returns INGEST_SIGNING_SECRET if set, otherwise falls back to effective_admin_secret."""
        return self.ingest_signing_secret or self.effective_admin_secret

    @property
    def effective_metrics_token(self) -> str:
        """METRICS_TOKEN, or "" when unset. No fallback to the admin secret (review
        P-15): a scraper credential must never double as the admin credential, so
        /metrics is disabled until a dedicated token is configured."""
        return self.metrics_token or ""

    @property
    def redis_durability_mode(self) -> str:
        if self.redis_url.startswith("rediss://"):
            return "managed-tls"
        if self.redis_appendonly:
            return f"appendonly:{self.redis_appendfsync}"
        return "ephemeral"


# Demo admin seeded only in development (scripts/seed.py). Login refuses it elsewhere.
DEV_SEED_ADMIN_EMAIL = "admin@runledger.local"

_KNOWN_WEAK_DEFAULTS = {
    "dev-secret-key-change-in-production",
    "change-me-in-production-32chars",
    "change-me-to-a-random-32char-string",
    "runledger-admin",
    "runledgerminio",
    "runledger",
}


def production_problems(s: Settings) -> list[str]:
    """Insecure settings that must not reach a production deployment (review P-14,
    technical review security #2). Empty in development."""
    if s.is_development:
        return []
    problems: list[str] = []
    if s.secret_key in _KNOWN_WEAK_DEFAULTS or len(s.secret_key) < 32:
        problems.append("SECRET_KEY is a known default or shorter than 32 characters")
    if s.admin_secret and (s.admin_secret in _KNOWN_WEAK_DEFAULTS or len(s.admin_secret) < 16):
        problems.append("ADMIN_SECRET is a known default or shorter than 16 characters")
    if s.database_url and ":runledger@" in s.database_url:
        problems.append(
            "DATABASE_URL uses the default password 'runledger' — change POSTGRES_PASSWORD"
        )
    if s.redis_url.startswith("redis://") and "@" not in s.redis_url:
        problems.append("REDIS_URL has no password — set REDIS_PASSWORD (or use rediss://)")
    origins = [o.strip() for o in s.cors_origins.split(",") if o.strip()]
    if "*" in origins:
        problems.append("CORS_ORIGINS must list explicit origins, not '*'")
    if s.metrics_token and len(s.metrics_token) < 16:
        problems.append("METRICS_TOKEN is shorter than 16 characters")
    if s.backup_enabled:
        secret = os.getenv("RUNLEDGER_BACKUP_SECRET_ACCESS_KEY", "")
        if secret in _KNOWN_WEAK_DEFAULTS:
            problems.append(
                "BACKUP_ENABLED with the default object-store secret — set "
                "RUNLEDGER_BACKUP_SECRET_ACCESS_KEY"
            )
    return problems


def _validate_production_secrets(s: Settings) -> None:
    problems = production_problems(s)
    if not problems:
        return
    import sys  # noqa: PLC0415

    level = "WARNING" if s.allow_insecure_defaults else "SECURITY ERROR"
    for p in problems:
        print(f"{level}: {p}", file=sys.stderr)
    if s.allow_insecure_defaults:
        return
    print(
        "Refusing to start in production with insecure settings. Fix the values above, "
        "set ENVIRONMENT=development for local work, or ALLOW_INSECURE_DEFAULTS=true for "
        "a throwaway demo.",
        file=sys.stderr,
    )
    raise SystemExit(1)


settings = Settings()
_validate_production_secrets(settings)
