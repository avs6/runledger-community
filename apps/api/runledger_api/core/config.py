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

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    # Admin secret for /admin/* endpoints.  If empty, falls back to secret_key.
    admin_secret: str = ""

    # App
    environment: str = "development"
    log_level: str = "INFO"
    runledger_mode: str = "community"

    # CORS — comma-separated list of allowed origins.
    # In production set CORS_ORIGINS=https://your-frontend.railway.app
    # Dev defaults cover the Next dev server (3000) and the Docker dashboard (3201) on
    # both localhost and 127.0.0.1 — a browser Origin that isn't listed fails preflight
    # (400) and the dashboard shows "Failed to load …" on client-fetched pages.
    cors_origins: str = (
        "http://localhost:3000,http://localhost:3201,http://127.0.0.1:3201"
    )

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
    app_base_url: str = "http://localhost:3000"  # used for verification links

    # Backup/restore — product-managed scheduler is opt-in while S3 setup matures.
    backup_enabled: bool = False

    # ── Operational metrics ───────────────────────────────────────────────────
    metrics_token: str = ""

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def effective_admin_secret(self) -> str:
        """Returns ADMIN_SECRET if set, otherwise falls back to SECRET_KEY."""
        return self.admin_secret or self.secret_key

    @property
    def effective_metrics_token(self) -> str:
        """Returns METRICS_TOKEN if set, otherwise falls back to effective_admin_secret."""
        return self.metrics_token or self.effective_admin_secret


settings = Settings()
