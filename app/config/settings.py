from __future__ import annotations
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

def _parse_listish(v: Optional[str]) -> List[str]:
    """Securely parse list-like strings, preventing JSON injection attacks"""
    if not v:
        return []
    s = v.strip()
    if not s:
        return []
    
    # Length validation to prevent DoS
    if len(s) > 10000:
        raise ValueError("Input string too long")
    
    # If it looks like JSON, validate it securely
    if s.startswith("[") and s.endswith("]"):
        import json
        try:
            # Parse JSON with strict validation
            data = json.loads(s)
            
            # Validate structure - must be a simple list
            if not isinstance(data, list):
                raise ValueError("Must be a list")
            
            # Validate list contents
            if len(data) > 100:  # Reasonable limit
                raise ValueError("List too long")
            
            result = []
            for item in data:
                # Only allow simple string/number types
                if not isinstance(item, (str, int, float)):
                    raise ValueError("List items must be strings or numbers")
                
                item_str = str(item).strip()
                # Validate string content
                if len(item_str) > 200:
                    raise ValueError("List item too long")
                
                # Basic validation - no dangerous characters
                if any(char in item_str for char in ['<', '>', '"', "'", '&', '\n', '\r']):
                    raise ValueError("Invalid characters in list item")
                
                if item_str:
                    result.append(item_str)
            
            return result
            
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            # If JSON parsing fails, fall back to comma-separated parsing
            pass
    
    # Secure comma-separated parsing
    items = []
    for item in s.split(","):
        item = item.strip()
        if len(item) > 200:
            continue  # Skip overly long items
        
        # Basic validation
        if any(char in item for char in ['<', '>', '"', "'", '\n', '\r']):
            continue  # Skip items with dangerous characters
        
        if item:
            items.append(item)
    
    return items[:100]  # Limit final result size

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
