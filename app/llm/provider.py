# app/llm/provider.py
from llama_index.core import Settings

def configure_llm(settings=None):
    """Configure global LLM in LlamaIndex Settings and return it."""
    if settings is None:
        from app.config.settings import get_settings
        settings = get_settings()
    
    provider = (settings.llm_provider or "ollama").lower()

    if provider == "ollama":
        from llama_index.llms.ollama import Ollama
        llm = Ollama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            request_timeout=180.0,
            additional_kwargs={"num_ctx": settings.ollama_num_ctx},
        )
        Settings.llm = llm
        print(f"✅ Configured Ollama with model: {settings.ollama_model}")
        return llm

    elif provider == "openai":
        import os
        if settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = settings.openai_api_key
        from llama_index.llms.openai import OpenAI
        llm = OpenAI(model=settings.openai_model)
        Settings.llm = llm
        return llm

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")