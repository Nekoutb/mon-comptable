from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Mon Comptable API"
    environment: str = "development"
    database_url: str = "sqlite:///./mon_comptable.db"
    jwt_secret: str = "development-only-change-me"
    token_minutes: int = 60
    storage_root: str = "./data/documents"
    max_upload_mb: int = 20
    redis_url: str = "redis://localhost:6379/0"
    background_mode: str = "inline"
    inbound_webhook_secret: str = "development-webhook-secret"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MC_", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def assert_secure(self) -> None:
        if self.environment == "production" and self.jwt_secret == "development-only-change-me":
            raise RuntimeError("MC_JWT_SECRET must be configured in production")
        if self.environment == "production" and self.inbound_webhook_secret == "development-webhook-secret":
            raise RuntimeError("MC_INBOUND_WEBHOOK_SECRET must be configured in production")


settings = Settings()
