from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "Creator Studio AI API"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://creator:creator@localhost:5433/creator_studio"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "development-only-change-this-secret-before-deploy"
    jwt_issuer: str = "creator-studio-ai"
    access_token_minutes: int = 60
    starter_credits: int = 30
    generation_credit_cost: int = 20
    model_provider: str = "disabled"
    model_api_base: str = ""
    model_api_key: str = ""
    cors_origins: str = "http://localhost:5199"
    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.environment.lower() == "production":
            if len(self.jwt_secret) < 32 or self.jwt_secret == "development-only-change-this-secret-before-deploy":
                raise ValueError("Production requires a unique JWT_SECRET of at least 32 characters")
            if "*" in self.cors_origin_list:
                raise ValueError("Wildcard CORS is forbidden in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
settings = get_settings()
