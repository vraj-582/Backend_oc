from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Full project endpoint — format:
    # https://{resource}.services.ai.azure.com/api/projects/{project-name}
    AZURE_PROJECT_ENDPOINT: str

    # Name of the published Foundry workflow (as shown in the portal)
    FOUNDRY_WORKFLOW_NAME: str = "Research-agent"

    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/research_assistant"
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    # JWT auth
    JWT_SECRET_KEY: str = "change-me-to-a-random-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    class Config:
        env_file = ".env"


settings = Settings()
