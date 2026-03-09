"""Application configuration loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DB_PATH: str = "memora.db"

    # Ollama / LLM
    OLLAMA_BASE_URL: str = "https://ollama.com/v1/"
    OLLAMA_API_KEY: str = ""
    OLLAMA_MODEL: str = "gpt-oss:20b"

    # Notification microservice
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8001"
    NOTIFICATION_API_KEY: str = ""

    # App
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.DB_PATH}"

    @property
    def db_path_resolved(self) -> Path:
        return Path(self.DB_PATH).resolve()


settings = Settings()
