"""Application configuration."""
from pydantic_settings import BaseSettings
import json, os

class Settings(BaseSettings):
    AT_USERNAME: str = "sandbox"
    AT_API_KEY: str = "atsk_7927eb27d29833c0880a43b4d65ace90d280117706372d5c6ccebb605fdc81c19fe0a450"
    AT_SENDER_ID: str = "AFRICASTKNG"
    DATABASE_URL: str = "sqlite+aiosqlite:///./nyeri_campaign.db"
    JWT_SECRET_KEY: str = "dev-secret-replace-in-production-with-64-char-hex"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    APP_NAME: str = "Nyeri Campaign App"
    DEBUG: bool = True
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:5173","http://localhost:8000","http://localhost:59642"]'

    @property
    def cors_origins_list(self):
        return json.loads(self.CORS_ORIGINS)

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
