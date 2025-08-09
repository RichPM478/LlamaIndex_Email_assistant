# app/embeddings/provider.py
from llama_index.core import Settings
import torch

def configure_embeddings(settings=None):
    """Configure embeddings with GPU support if available"""
    if settings is None:
        from app.config.settings import get_settings
        settings = get_settings()
    
    provider = (settings.embeddings_provider or 'local_hf').lower()

    if provider == 'local_hf':
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        
        # Auto-detect GPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        if device == "cuda":
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"🚀 GPU ENABLED for Embeddings!")
            print(f"   GPU: {gpu_name}")
            print(f"   VRAM: {vram_gb:.1f} GB")
            torch.cuda.empty_cache()
        else:
            print("⚠️ Running embeddings on CPU")
        
        # Create embedding model - WITHOUT batch_size parameter
        embed = HuggingFaceEmbedding(
            model_name=settings.embedding_model,
            device=device,
            # Don't pass batch_size here - it's not a valid parameter
            # max_length is also not valid for HuggingFaceEmbedding
        )
        
        # Set batch size after initialization if needed
        # This is handled internally by the model
        
        Settings.embed_model = embed
        print(f"✅ Configured embeddings: {settings.embedding_model} on {device.upper()}")
        return embed
    
    elif provider == 'openai':
        from llama_index.embeddings.openai import OpenAIEmbedding
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY required for OpenAI embeddings")
        embed = OpenAIEmbedding(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key
        )
        Settings.embed_model = embed
        return embed
    
    else:
        raise ValueError(f"Unknown embeddings provider: {provider}")