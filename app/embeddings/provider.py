from llama_index.core import Settings
from app.config.settings import Settings as AppSettings

from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding

def configure_embeddings(app_settings: AppSettings):
    provider = (app_settings.embeddings_provider or 'local_hf').lower()

    if provider == 'local_hf':
        embed = HuggingFaceEmbedding(model_name=app_settings.embedding_model)
    elif provider == 'openai':
        if not app_settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for EMBEDDINGS_PROVIDER=openai")
        embed = OpenAIEmbedding(
            model=app_settings.openai_embedding_model,
            api_key=app_settings.openai_api_key
        )
    else:
        raise ValueError(f"Unknown EMBEDDINGS_PROVIDER: {provider}")

    Settings.embed_model = embed
    return embed
