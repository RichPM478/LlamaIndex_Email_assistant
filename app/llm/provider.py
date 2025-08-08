from __future__ import annotations
import os
from llama_index.core import Settings
from app.config.settings import get_settings

def configure_llm(settings=None):
    """Configure global LLM in LlamaIndex Settings and return it."""
    s = settings or get_settings()
    provider = (s.llm_provider or "ollama").lower()

    if provider == "ollama":
        from llama_index.llms.ollama import Ollama
        num_ctx = getattr(s, "ollama_num_ctx", 2048)  # NEW: pass from settings
        llm = Ollama(
            base_url=s.ollama_base_url,
            model=s.ollama_model,
            request_timeout=180.0,
            additional_kwargs={"num_ctx": num_ctx},
        )
        Settings.llm = llm
        return llm

    if provider == "openai":
        if s.openai_api_key:
            os.environ["OPENAI_API_KEY"] = s.openai_api_key
        from llama_index.llms.openai import OpenAI
        llm = OpenAI(model=s.openai_model)
        Settings.llm = llm
        return llm

    if provider == "azure_openai":
        if s.azure_openai_api_key:
            os.environ["AZURE_OPENAI_API_KEY"] = s.azure_openai_api_key
        if s.azure_openai_endpoint:
            os.environ["AZURE_OPENAI_ENDPOINT"] = s.azure_openai_endpoint
        if s.azure_openai_api_version:
            os.environ["AZURE_OPENAI_API_VERSION"] = s.azure_openai_api_version
        from llama_index.llms.openai import AzureOpenAI
        llm = AzureOpenAI(
            engine=s.azure_openai_deployment or "gpt-4o-mini",
            api_key=s.azure_openai_api_key or None,
            api_base=s.azure_openai_endpoint or None,
            api_version=s.azure_openai_api_version or None,
        )
        Settings.llm = llm
        return llm

    if provider == "anthropic":
        if s.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = s.anthropic_api_key
        from llama_index.llms.anthropic import Anthropic
        llm = Anthropic(model=s.anthropic_model)
        Settings.llm = llm
        return llm

    raise ValueError(f"Unknown LLM provider: {provider}")

