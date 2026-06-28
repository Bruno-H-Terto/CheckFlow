from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    ENV: Literal["test", "development", "production"] = "development"
    SQLITE_DATABASE_PATH: str = "./checkflow.db"
    DATABASE_URL: str = (
        "postgresql+psycopg://checkflow:checkflow@localhost:5432/checkflow"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

settings = Settings()
