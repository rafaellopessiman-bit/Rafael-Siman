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
    top_k: int = Field(default=5, alias="TOP_K")
    llm_cache_enabled: bool = Field(default=True, alias="LLM_CACHE_ENABLED")
    llm_cache_max_size: int = Field(default=1000, alias="LLM_CACHE_MAX_SIZE")
    llm_cache_persistent: bool = Field(default=False, alias="LLM_CACHE_PERSISTENT")
    llm_cache_path: str = Field(default="data/llm_cache.db", alias="LLM_CACHE_PATH")
    llm_cache_ttl_seconds: Optional[int] = Field(default=None, alias="LLM_CACHE_TTL_SECONDS")
    database_path: str = Field(default="data/atlas_local.db", alias="DATABASE_PATH")
    pdf_ocr_enabled: bool = Field(default=False, alias="PDF_OCR_ENABLED")
    pdf_ocr_command: str = Field(default="ocrmypdf", alias="PDF_OCR_COMMAND")
    pdf_ocr_language: str = Field(default="eng", alias="PDF_OCR_LANGUAGE")
    image_ocr_enabled: bool = Field(default=False, alias="IMAGE_OCR_ENABLED")
    image_ocr_command: str = Field(default="tesseract", alias="IMAGE_OCR_COMMAND")
    image_ocr_language: str = Field(default="eng", alias="IMAGE_OCR_LANGUAGE")
    schedule_eval_queries_path: str = Field(default="data/eval_queries.json", alias="SCHEDULE_EVAL_QUERIES_PATH")
    schedule_eval_baseline_path: str = Field(default="data/eval_baseline.json", alias="SCHEDULE_EVAL_BASELINE_PATH")
    schedule_eval_top_k: int = Field(default=5, alias="SCHEDULE_EVAL_TOP_K")
    schedule_notify_webhook_url: Optional[str] = Field(default=None, alias="SCHEDULE_NOTIFY_WEBHOOK_URL")
    schedule_notify_timeout_seconds: int = Field(default=10, alias="SCHEDULE_NOTIFY_TIMEOUT_SECONDS")
    schedule_notify_on: str = Field(default="on-issues", alias="SCHEDULE_NOTIFY_ON")
    schedule_notify_format: str = Field(default="raw", alias="SCHEDULE_NOTIFY_FORMAT")
    watch_interval_seconds: int = Field(default=30, alias="WATCH_INTERVAL_SECONDS")
    watch_remediation_policy: str = Field(default="full-auto", alias="WATCH_REMEDIATION_POLICY")
    remediation_isolate_flags: tuple[str, ...] = Field(
        default=(
            "no_usable_chunks",
            "very_short_document",
            "repetitive_content",
            "numeric_heavy",
            "low_vocabulary_document",
        ),
        alias="REMEDIATION_ISOLATE_FLAGS",
    )

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

    @field_validator("schedule_eval_top_k")
    @classmethod
    def validate_schedule_eval_top_k(cls, value: int) -> int:
        if value < 1:
            raise ValueError("SCHEDULE_EVAL_TOP_K deve ser maior ou igual a 1.")
        return value

    @field_validator("llm_cache_max_size")
    @classmethod
    def validate_llm_cache_max_size(cls, value: int) -> int:
        if value < 1:
            raise ValueError("LLM_CACHE_MAX_SIZE deve ser maior ou igual a 1.")
        return value

    @field_validator("schedule_notify_webhook_url")
    @classmethod
    def validate_schedule_notify_webhook_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = value.strip()
        return text or None

    @field_validator("schedule_notify_timeout_seconds")
    @classmethod
    def validate_schedule_notify_timeout_seconds(cls, value: int) -> int:
        if value < 1:
            raise ValueError("SCHEDULE_NOTIFY_TIMEOUT_SECONDS deve ser maior ou igual a 1.")
        return value

    @field_validator("schedule_notify_on")
    @classmethod
    def validate_schedule_notify_on(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"always", "on-error", "on-issues", "never"}:
            raise ValueError("SCHEDULE_NOTIFY_ON deve ser one of: always, on-error, on-issues, never.")
        return normalized

    @field_validator("schedule_notify_format")
    @classmethod
    def validate_schedule_notify_format(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"raw", "teams", "slack"}:
            raise ValueError("SCHEDULE_NOTIFY_FORMAT deve ser one of: raw, teams, slack.")
        return normalized

    @field_validator("watch_interval_seconds")
    @classmethod
    def validate_watch_interval_seconds(cls, value: int) -> int:
        if value < 1:
            raise ValueError("WATCH_INTERVAL_SECONDS deve ser maior ou igual a 1.")
        return value

    @field_validator("watch_remediation_policy")
    @classmethod
    def validate_watch_remediation_policy(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"manual", "ocr-required", "full-auto"}:
            raise ValueError("WATCH_REMEDIATION_POLICY deve ser one of: manual, ocr-required, full-auto.")
        return normalized

    @field_validator(
        "pdf_ocr_command",
        "pdf_ocr_language",
        "image_ocr_command",
        "image_ocr_language",
    )
    @classmethod
    def validate_non_empty_text_fields(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Campo de OCR nao pode ser vazio.")
        return text

    @field_validator("remediation_isolate_flags", mode="before")
    @classmethod
    def validate_remediation_isolate_flags(cls, value: object) -> tuple[str, ...]:
        if value is None:
            return ()

        if isinstance(value, str):
            items = [item.strip().lower() for item in value.split(",") if item.strip()]
            return tuple(dict.fromkeys(items))

        if isinstance(value, (list, tuple, set, frozenset)):
            items = [str(item).strip().lower() for item in value if str(item).strip()]
            return tuple(dict.fromkeys(items))

        raise ValueError("REMEDIATION_ISOLATE_FLAGS deve ser string CSV ou lista de flags.")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        raise AtlasConfigError(f"Erro de configuração: {exc}") from exc
