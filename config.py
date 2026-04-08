from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from db.models import Project
from sqlmodel import select

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

    def update_settings(self):
        # update project settings in database
        from db.state import create_db_and_tables
        session = create_db_and_tables()
        
        statement = select(Project).where(Project.id == self.id)
        project = session.exec(statement).first()
        if project:
            project.name = self.name
            project.description = self.description
            project.project_path = self.project_path
            project.figma_database_name = self.figma_database_name
            project.figma_file_key = self.figma_file_key
            project.sanity_project_id = self.sanity_project_id
            project.sanity_dataset = self.sanity_dataset
            project.sanity_api_read_token = self.sanity_api_read_token
            project.started_at = self.started_at
            project.updated_at = self.updated_at
            session.add(project)
            session.commit()
            session.refresh(project)
        else:
            # create new project
            project = Project(
                id=self.id,
                name=self.name,
                description=self.description,
                project_path=self.project_path,
                figma_database_name=self.figma_database_name,
                figma_file_key=self.figma_file_key,
                sanity_project_id=self.sanity_project_id,
                sanity_dataset=self.sanity_dataset,
                sanity_api_read_token=self.sanity_api_read_token,
                started_at=self.started_at,
                updated_at=self.updated_at,
            )
            session.add(project)
            session.commit()
            session.refresh(project)


settings = Settings()
