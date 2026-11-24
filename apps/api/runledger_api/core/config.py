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
    # Dedicated secret for gateway-rs -> API /gateway/runtime/internal/* calls
    # (review tr-security / cd:S-05). When set, those endpoints accept only this
    # token (x-gateway-internal-token) and no longer the shared ADMIN_SECRET.
    gateway_internal_token: str = ""
    # Dedicated secret for mcp-gateway -> API key resolution (same header).
    mcp_internal_token: str = ""
    # Secrets at rest (core/secrets.py): comma-separated Fernet keys or passphrases
    # (first one encrypts), and an optional AWS KMS key for envelope encryption.
    secrets_master_key: str = ""
    secrets_kms_key_id: str = ""
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
    environment: str = "development"
    log_level: str = "INFO"
    runledger_mode: str = "community"

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

    # Feature-flag and infra controls
    feature_flags: str = ""
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
    analytics_rate_limit_per_minute: int = 0
    management_rate_limit_per_minute: int = 0
    system_rate_limit_per_minute: int = 600

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
    def enabled_feature_flags(self) -> set[str]:
        return {flag.strip() for flag in self.feature_flags.split(",") if flag.strip()}

    def is_feature_enabled(self, flag: str) -> bool:
        return flag in self.enabled_feature_flags

    @property
    def redis_durability_mode(self) -> str:
        if self.redis_url.startswith("rediss://"):
            return "managed-tls"
        if self.redis_appendonly:
            return f"appendonly:{self.redis_appendfsync}"
        return "ephemeral"


_KNOWN_WEAK_DEFAULTS = {
    "dev-secret-key-change-in-production",
    "change-me-in-production-32chars",
    "change-me-to-a-random-32char-string",
    "runledger-admin",
}


def _validate_production_secrets(s: Settings) -> None:
    if s.environment == "development":
        return
    problems: list[str] = []
    if s.secret_key in _KNOWN_WEAK_DEFAULTS:
        problems.append("SECRET_KEY is a known default — set a real 32+ char random string")
    if s.admin_secret in _KNOWN_WEAK_DEFAULTS:
        problems.append("ADMIN_SECRET is a known default — set a real random string")
    if s.database_url and "runledger:runledger@" in s.database_url:
        problems.append(
            "DATABASE_URL uses the default password 'runledger' — change POSTGRES_PASSWORD"
        )
    if problems:
        import sys

        for p in problems:
            print(f"SECURITY ERROR: {p}", file=sys.stderr)
        raise SystemExit(1)


settings = Settings()
_validate_production_secrets(settings)
