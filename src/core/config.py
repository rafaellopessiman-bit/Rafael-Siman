from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.exceptions import AtlasConfigError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    groq_api_key: str = Field(..., alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    documents_path: Path = Field(default=Path("data/entrada"), alias="DOCUMENTS_PATH")
    top_k: int = Field(default=3, alias="TOP_K")
    llm_cache_enabled: bool = Field(default=True, alias="LLM_CACHE_ENABLED")
    llm_cache_max_size: int = Field(default=1000, alias="LLM_CACHE_MAX_SIZE")
    llm_cache_persistent: bool = Field(default=False, alias="LLM_CACHE_PERSISTENT")
    llm_cache_path: str = Field(default="data/llm_cache.db", alias="LLM_CACHE_PATH")
    llm_cache_ttl_seconds: Optional[int] = Field(default=None, alias="LLM_CACHE_TTL_SECONDS")
    database_path: str = Field(default="data/atlas_local.db", alias="DATABASE_PATH")

    @field_validator("groq_api_key")
    @classmethod
    def validate_groq_api_key(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("GROQ_API_KEY está ausente ou vazio.")
        return value.strip()

    @field_validator("groq_model")
    @classmethod
    def validate_groq_model(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("GROQ_MODEL está ausente ou vazio.")
        return value.strip()

    @field_validator("documents_path", mode="before")
    @classmethod
    def validate_documents_path(cls, value: str | Path) -> Path:
        path = Path(value).expanduser()
        if not str(path).strip():
            raise ValueError("DOCUMENTS_PATH está ausente ou vazio.")
        return path

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, value: int) -> int:
        if value < 1:
            raise ValueError("TOP_K deve ser maior ou igual a 1.")
        return value

    @field_validator("llm_cache_max_size")
    @classmethod
    def validate_llm_cache_max_size(cls, value: int) -> int:
        if value < 1:
            raise ValueError("LLM_CACHE_MAX_SIZE deve ser maior ou igual a 1.")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        raise AtlasConfigError(f"Erro de configuração: {exc}") from exc
