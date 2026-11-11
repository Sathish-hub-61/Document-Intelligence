"""
Configuration and tunable settings for University Document Intelligence.
Uses pydantic-settings to load from environment variables and .env file.
"""
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = Field(default="sqlite:///./university_doc_intel.db", alias="DATABASE_URL")

    # Storage and ChromaDB paths
    chroma_path: str = Field(default="./chroma_db", alias="CHROMA_PATH")
    storage_path: str = Field(default="./storage", alias="STORAGE_PATH")

    # Authentication & Security
    jwt_secret: str = Field(default="super-secret-development-jwt-key-replace-in-production-12345", alias="JWT_SECRET")
    jwt_expire_minutes: int = Field(default=30, alias="JWT_EXPIRE_MINUTES")
    argon2_min_password_length: int = Field(default=10, alias="ARGON2_MIN_PASSWORD_LENGTH")

    # LLM Settings
    llm_provider: str = Field(default="fake", alias="LLM_PROVIDER")  # gemini, openai, fake
    llm_model: str = Field(default="fake-model", alias="LLM_MODEL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_temperature: float = Field(default=0.1, alias="LLM_TEMPERATURE")
    llm_max_output_tokens: int = Field(default=500, alias="LLM_MAX_OUTPUT_TOKENS")

    # Embeddings & Chunking
    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5", alias="EMBEDDING_MODEL")
    chunk_tokens: int = Field(default=600, alias="CHUNK_TOKENS")
    chunk_overlap: int = Field(default=80, alias="CHUNK_OVERLAP")

    # Retrieval Tuning Parameters
    top_k_vector: int = Field(default=20, alias="TOP_K_VECTOR")
    top_k_keyword: int = Field(default=20, alias="TOP_K_KEYWORD")
    top_k_final: int = Field(default=8, alias="TOP_K_FINAL")
    min_evidence_score: float = Field(default=0.015, alias="MIN_EVIDENCE_SCORE")

    # File Upload Limits
    max_upload_mb: int = Field(default=25, alias="MAX_UPLOAD_MB")

    # Web & CORS
    allowed_origins: str = Field(default="http://localhost:5173,http://localhost:3000", alias="ALLOWED_ORIGINS")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


_settings_instance: Settings | None = None


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance

