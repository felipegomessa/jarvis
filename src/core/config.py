"""Configuração tipada via pydantic-settings — RF-001.4 / ADR D-009.

Carrega variáveis JARVIS_* do shell (prioridade alta) ou do arquivo `.env`
(prioridade baixa), com defaults sensatos. Singleton via `@lru_cache`.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="JARVIS_",
        case_sensitive=False,
        extra="ignore",
    )

    # ----- LLM -----
    llm_base_url: HttpUrl = Field(
        default=HttpUrl("https://llm.liaufms.org/v1/gemma-3-12b-it")
    )
    llm_model: str = Field(default="google/gemma-3-12b-it")
    llm_api_key: str = Field(...)  # obrigatório, sem default
    llm_timeout_s: float = Field(default=60.0, gt=0)
    llm_max_tokens: int = Field(default=2048, gt=0)
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    # ----- DB -----
    db_path: Path = Field(default=Path("./data/jarvis.db"))

    # ----- RAG / embeddings -----
    embed_model: str = Field(default="intfloat/multilingual-e5-small")
    chunk_size: int = Field(default=800, gt=0)
    chunk_overlap: int = Field(default=150, ge=0)
    rag_top_k: int = Field(default=5, gt=0)
    rag_distance_threshold: float = Field(default=0.6, ge=0.0, le=2.0)

    # ----- Logging -----
    log_level: str = Field(default="INFO")
    log_dir: Path = Field(default=Path("./logs"))

    # ----- UI -----
    ui_host: str = Field(default="127.0.0.1")
    ui_port: int = Field(default=8080, gt=0, lt=65536)
    ui_dark: bool = Field(default=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton de Settings (carrega uma vez por processo)."""
    return Settings()  # type: ignore[call-arg]
