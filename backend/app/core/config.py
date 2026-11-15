from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings managed via pydantic-settings.
    Reads environment variables from system environment and/or .env file.
    """
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Project metadata
    project_name: str = "Yojana Saathi API"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True

    # Routing prefix
    api_v1_prefix: str = "/api/v1"

    # CORS configuration for local React + Vite frontend
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Database connection string (defaulting to zero-cost local SQLite)
    database_url: str = "sqlite+aiosqlite:///./app.db"

    # LLM Provider Gateway Configuration
    # Supported providers: "deterministic", "ollama", "groq", "gemini"
    llm_primary_provider: str = "groq"
    llm_secondary_provider: Optional[str] = None

    # Local Ollama Settings (Optional Local AI Provider)
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_timeout_seconds: float = 10.0

    # Groq Cloud LLM Settings
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_timeout_seconds: float = 12.0
    groq_nlu_timeout_seconds: float = 6.0
    groq_synthesis_timeout_seconds: float = 7.0

    # Google Gemini Settings (Legacy / Backward Compatibility)
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_timeout_seconds: float = 12.0
    gemini_nlu_timeout_seconds: float = 6.0
    gemini_synthesis_timeout_seconds: float = 7.0


settings = Settings()

