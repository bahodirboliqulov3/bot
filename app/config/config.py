from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str = Field(..., description="Telegram bot API token")
    OWNER_ID: int = Field(..., description="Initial owner telegram ID")

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/test_platform_db",
        description="Async SQLAlchemy database URL"
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )

    DEBUG: bool = Field(default=False)
    PAGE_SIZE: int = Field(default=10)
    TIMEZONE: str = Field(default="Asia/Tashkent")

    CERTIFICATE_DIR: Path = Field(default=Path("./storage/certificates"))
    EXCEL_DIR: Path = Field(default=Path("./storage/exports"))
    UPLOAD_DIR: Path = Field(default=Path("./storage/uploads"))
    DATA_DIR: Path = Field(default=Path("./storage/data"))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure storage directories exist
settings.CERTIFICATE_DIR.mkdir(parents=True, exist_ok=True)
settings.EXCEL_DIR.mkdir(parents=True, exist_ok=True)
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
