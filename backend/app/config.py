from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://stockbook:password@localhost:5432/stockbook"

    SECRET_KEY: str = "insecure-dev-secret-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    SEED_USERNAME: str = "admin"
    SEED_EMAIL: str = "admin@stockbook.local"
    SEED_PASSWORD: str = "changeme"

    PRICE_UPDATE_INTERVAL_MINUTES: int = 5
    ENABLE_SCHEDULER: bool = True

    ENVIRONMENT: str = "development"
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()
