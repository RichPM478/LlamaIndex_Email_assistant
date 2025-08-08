from __future__ import annotations
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

def _parse_listish(v: Optional[str]) -> List[str]:
    """Accepts: empty -> [], 'a,b' -> ['a','b'], JSON list -> list"""
    if not v:
        return []
    s = v.strip()
    if not s:
        return []
    if s.startswith("["):
        import json
        try:
            data = json.loads(s)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
        except Exception:
            pass
    return [item.strip() for item in s.split(",") if item.strip()]

class Settings(BaseSettings):
    # ---------- LLM provider ----------
    llm_provider: str = Field("ollama", env="LLM_PROVIDER")

    # Ollama
    ollama_model: str = Field("llama3.2:3b", env="OLLAMA_MODEL")
    ollama_base_url: str = Field("http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_num_ctx: int = Field(2048, env="OLLAMA_NUM_CTX")  # NEW FIELD

    # OpenAI
    openai_api_key: str = Field("", env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o-mini", env="OPENAI_MODEL")

    # Azure OpenAI
    azure_openai_api_key: str = Field("", env="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: str = Field("", env="AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment: str = Field("", env="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = Field("2024-06-01", env="AZURE_OPENAI_API_VERSION")

    # Anthropic
    anthropic_api_key: str = Field("", env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field("claude-3-haiku-20240307", env="ANTHROPIC_MODEL")

    # ---------- Embeddings ----------
    embeddings_provider: str = Field("local_hf", env="EMBEDDINGS_PROVIDER")  # local_hf | openai
    embedding_model: str = Field("sentence-transformers/all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    openai_embedding_model: str = Field("text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL")

    # ---------- IMAP ----------
    imap_host: str = Field(..., env="IMAP_HOST")
    imap_port: int = Field(993, env="IMAP_PORT")
    imap_ssl: bool = Field(True, env="IMAP_SSL")
    imap_user: str = Field(..., env="IMAP_USER")
    imap_password: str = Field(..., env="IMAP_PASSWORD")
    imap_folder: str = Field("INBOX", env="IMAP_FOLDER")

    # Raw string filters (parsed to lists by properties)
    filter_from_raw: Optional[str] = Field(default=None, env="FILTER_FROM")
    filter_subject_raw: Optional[str] = Field(default=None, env="FILTER_SUBJECT")

    # ---------- App ----------
    app_timezone: str = Field("Europe/London", env="APP_TIMEZONE")
    week_start: str = Field("Monday", env="WEEK_START")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def filter_from(self) -> List[str]:
        return _parse_listish(self.filter_from_raw)

    @property
    def filter_subject(self) -> List[str]:
        return _parse_listish(self.filter_subject_raw)

def get_settings() -> Settings:
    return Settings()
