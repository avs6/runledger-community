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
    runledger_mode: str = "oss"  # "oss" | "cloud"

    # CORS — comma-separated list of allowed origins.
    # In production set CORS_ORIGINS=https://your-frontend.railway.app
    cors_origins: str = "http://localhost:3000"

    # Provider pricing YAML file.  Mounted into the container by docker-compose.
    # Set PRICING_FILE=/path/to/pricing.yml to override.
    pricing_file: str = "/app/config/pricing.yml"

    # Email — Brevo SMTP (leave empty to disable email sending)
    smtp_host: str = "smtp-relay.brevo.com"
    smtp_port: int = 587
    smtp_user: str = ""  # Brevo login email
    smtp_password: str = ""  # Brevo SMTP key
    smtp_from: str = "runledger@gmail.com"
    app_base_url: str = "http://localhost:3000"  # used for verification links

    # Stripe — leave empty for OSS / self-hosted deployments
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""  # Stripe Price ID for Starter plan
    stripe_price_growth: str = ""  # Stripe Price ID for Growth plan
    stripe_price_enterprise: str = ""  # Stripe Price ID for Enterprise plan

    # Firebase Admin SDK — leave empty to disable social login
    # Create a service account at: Firebase Console → Project Settings → Service Accounts
    firebase_project_id: str = ""
    firebase_client_email: str = ""
    firebase_private_key: str = ""  # PEM key; \n in value is auto-converted

    # ── BYOK / KMS (enterprise) ───────────────────────────────────────────────
    # KMS_PROVIDER=local (default) | aws_kms | vault
    kms_provider: str = "local"

    # AWS KMS — requires boto3 and IAM permissions for kms:GenerateDataKey + kms:Decrypt
    aws_kms_key_id: str = ""       # e.g. arn:aws:kms:us-east-1:123456:key/abc-def
    aws_kms_region: str = "us-east-1"

    # HashiCorp Vault Transit secrets engine
    vault_addr: str = ""           # e.g. https://vault.example.com
    vault_token: str = ""          # Vault token with transit encrypt/decrypt policy
    vault_transit_key: str = "runledger"  # Transit key name

    # ── Operational metrics ───────────────────────────────────────────────────
    # Token required to scrape /metrics and /ops/status.
    # If empty, falls back to effective_admin_secret.
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
