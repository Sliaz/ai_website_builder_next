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

    # Project settings
    id: str = ""
    name: str = ""
    description: str = ""
    project_path: str = ""
    figma_database_name: str = ""
    figma_file_key: str = ""
    sanity_project_id: str = ""
    sanity_dataset: str = ""
    sanity_api_read_token: str = ""
    started_at: Optional[str] = None
    updated_at: Optional[str] = None

    dev: bool = False


settings = Settings()
