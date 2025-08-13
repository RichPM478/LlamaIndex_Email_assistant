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
            print(f"[GPU] Embeddings will use GPU acceleration")
            print(f"   GPU: {gpu_name}")
            print(f"   VRAM: {vram_gb:.1f} GB")
            torch.cuda.empty_cache()
        else:
            print("[CPU] Running embeddings on CPU")
        
        # Create embedding model directly with the correct device
        # The HuggingFaceEmbedding class accepts device as a parameter
        try:
            # First try loading directly to the desired device
            embed = HuggingFaceEmbedding(
                model_name=settings.embedding_model,
                device=device,  # Pass the device directly
                trust_remote_code=True,
                cache_folder=None,
                embed_batch_size=64 if device == "cuda" else 10,  # Optimized for RTX 4070
            )
            print(f"[SUCCESS] Configured embeddings: {settings.embedding_model} on {device.upper()}")
            print(f"   Model dimensions: 1024 (high-quality dense embeddings)")
            print(f"   Context window: 512 tokens")
            print(f"   Batch size: {64 if device == 'cuda' else 10}")
            
        except Exception as e:
            print(f"[WARNING] Failed to load model on {device}: {e}")
            print("[WARNING] Attempting fallback to CPU...")
            
            # Fallback to CPU if GPU fails
            try:
                embed = HuggingFaceEmbedding(
                    model_name=settings.embedding_model,
                    device="cpu",
                    trust_remote_code=False,
                    embed_batch_size=10,
                )
                print(f"[SUCCESS] Configured embeddings: {settings.embedding_model} on CPU (fallback)")
                
            except Exception as cpu_error:
                print(f"[ERROR] Failed to load embeddings model: {cpu_error}")
                raise
        
        Settings.embed_model = embed
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