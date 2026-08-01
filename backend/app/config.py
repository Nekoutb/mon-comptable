from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Mon Comptable API"
    environment: str = "development"
    database_url: str = "sqlite:///./mon_comptable.db"
    jwt_secret: str = "development-only-change-me"
    token_minutes: int = 60
    storage_root: str = "./data/documents"
    max_upload_mb: int = 20
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MC_", extra="ignore")

    def assert_secure(self) -> None:
        if self.environment == "production" and self.jwt_secret == "development-only-change-me":
            raise RuntimeError("MC_JWT_SECRET must be configured in production")


settings = Settings()
