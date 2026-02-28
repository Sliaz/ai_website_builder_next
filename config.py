from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    figma_api_key: Optional[str] = None
    dev: bool = False


settings = Settings()
