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

    # App
    environment: str = "development"
    log_level: str = "INFO"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


settings = Settings()
