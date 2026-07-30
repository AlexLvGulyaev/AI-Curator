"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AI Curator backend configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    debug: bool = False
    secret_key: str = "CHANGE_ME"

    # Operational database
    database_url: str = "postgresql+asyncpg://ai_curator:ai_curator@localhost:5432/ai_curator"

    # Chroma vector store
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # Document store for Knowledge Base
    doc_store_path: str = "./storage/documents"

    # LMS Adapter
    lms_base_url: str = "https://lms.example.com"
    lms_api_token: str = "YOUR_MOODLE_API_TOKEN"

    # LLM Provider
    openai_api_key: str = "YOUR_OPENAI_API_KEY"
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Public URLs
    web_ui_url: str = "https://curator.example.com"
    admin_console_url: str = "https://curator-admin.example.com"
    backend_api_url: str = "https://curator-api.example.com"

    # Admin Console authentication
    admin_console_token: str = ""

    # Log retention and archiving
    archive_dir: str = "./storage/archives"
    hot_retention_days: int = 30
    trace_retention_days: int = 7

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def admin_auth_enabled(self) -> bool:
        return bool(self.admin_console_token) and not self.admin_console_token.startswith("YOUR")


settings = Settings()
