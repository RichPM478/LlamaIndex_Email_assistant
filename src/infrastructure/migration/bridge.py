"""Bridge module to connect existing code with new modular architecture."""
import os
import sys
from pathlib import Path
from typing import Optional, Any, Dict
import asyncio

# Add paths for compatibility
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.infrastructure.config.settings import get_config
from src.infrastructure.config.provider_factory import (
    create_model_provider,
    create_embedding_provider
)
from src.core.application.interfaces.model_provider import (
    IModelProvider,
    IEmbeddingProvider
)


class LegacyLLMBridge:
    """Bridge to make new providers work with existing LlamaIndex code."""
    
    def __init__(self, provider: Optional[str] = None):
        """Initialize the bridge with a specific provider."""
        self.provider_name = provider or get_config().get_default_provider("models")
        self.provider: Optional[IModelProvider] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the provider."""
        if not self._initialized:
            self.provider = await create_model_provider(self.provider_name)
            self._initialized = True
    
    def complete(self, prompt: str, **kwargs) -> str:
        """Synchronous completion method for compatibility."""
        if not self._initialized:
            asyncio.run(self.initialize())
        
        # Run async method synchronously
        response = asyncio.run(self.provider.generate(prompt, **kwargs))
        return response.content
    
    async def acomplete(self, prompt: str, **kwargs) -> str:
        """Async completion method."""
        if not self._initialized:
            await self.initialize()
        
        response = await self.provider.generate(prompt, **kwargs)
        return response.content
    
    def stream_complete(self, prompt: str, **kwargs):
        """Streaming completion for compatibility."""
        if not self._initialized:
            asyncio.run(self.initialize())
        
        async def _stream():
            async for chunk in self.provider.generate_stream(prompt, **kwargs):
                yield chunk
        
        # Convert async generator to sync
        loop = asyncio.new_event_loop()
        gen = _stream()
        try:
            while True:
                chunk = loop.run_until_complete(gen.__anext__())
                yield chunk
        except StopAsyncIteration:
            pass
        finally:
            loop.close()


class LegacyEmbeddingBridge:
    """Bridge to make new embedding providers work with existing code."""
    
    def __init__(self, provider: Optional[str] = None):
        """Initialize the bridge with a specific provider."""
        self.provider_name = provider or get_config().get_default_provider("embeddings")
        self.provider: Optional[IEmbeddingProvider] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the provider."""
        if not self._initialized:
            self.provider = await create_embedding_provider(self.provider_name)
            self._initialized = True
    
    def get_text_embedding(self, text: str) -> list:
        """Synchronous embedding method for compatibility."""
        if not self._initialized:
            asyncio.run(self.initialize())
        
        response = asyncio.run(self.provider.embed(text))
        return response.embeddings
    
    async def aget_text_embedding(self, text: str) -> list:
        """Async embedding method."""
        if not self._initialized:
            await self.initialize()
        
        response = await self.provider.embed(text)
        return response.embeddings
    
    def get_text_embedding_batch(self, texts: list, **kwargs) -> list:
        """Batch embedding for compatibility."""
        if not self._initialized:
            asyncio.run(self.initialize())
        
        responses = asyncio.run(self.provider.embed_batch(texts))
        return [r.embeddings for r in responses]


def configure_llm_from_new_config(provider: Optional[str] = None) -> Any:
    """
    Create a LlamaIndex-compatible LLM from new configuration.
    This function bridges the gap between old and new architecture.
    """
    config = get_config()
    provider_name = provider or config.get_default_provider("models")
    
    # Check if it's Gemini
    if provider_name == "gemini":
        # Return our bridge that mimics LlamaIndex LLM interface
        return LegacyLLMBridge(provider_name)
    
    # For other providers, try to use existing LlamaIndex implementations
    elif provider_name == "openai":
        try:
            from llama_index.llms.openai import OpenAI
            model_config = config.get_model_config("models")
            return OpenAI(
                model=model_config.get("model_name", "gpt-4-turbo-preview"),
                api_key=model_config.get("api_key") or os.getenv("OPENAI_API_KEY"),
                temperature=model_config.get("temperature", 0.7),
                max_tokens=model_config.get("max_tokens", 2000)
            )
        except ImportError:
            # Fallback to bridge
            return LegacyLLMBridge(provider_name)
    
    elif provider_name == "ollama":
        try:
            from llama_index.llms.ollama import Ollama
            model_config = config.get_model_config("models")
            return Ollama(
                model=model_config.get("model_name", "llama3"),
                base_url=model_config.get("endpoint", "http://localhost:11434"),
                temperature=model_config.get("temperature", 0.7)
            )
        except ImportError:
            return LegacyLLMBridge(provider_name)
    
    # Default to bridge
    return LegacyLLMBridge(provider_name)


def configure_embedding_from_new_config(provider: Optional[str] = None) -> Any:
    """
    Create a LlamaIndex-compatible embedding model from new configuration.
    """
    config = get_config()
    provider_name = provider or config.get_default_provider("embeddings")
    
    # Check if it's Gemini
    if provider_name == "gemini":
        return LegacyEmbeddingBridge(provider_name)
    
    # For other providers, try existing implementations
    elif provider_name == "openai":
        try:
            from llama_index.embeddings.openai import OpenAIEmbedding
            model_config = config.get_model_config("embeddings")
            return OpenAIEmbedding(
                model=model_config.get("model_name", "text-embedding-3-small"),
                api_key=model_config.get("api_key") or os.getenv("OPENAI_API_KEY")
            )
        except ImportError:
            return LegacyEmbeddingBridge(provider_name)
    
    elif provider_name == "sentence-transformers":
        try:
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            model_config = config.get_model_config("embeddings")
            return HuggingFaceEmbedding(
                model_name=model_config.get("model_name", "all-MiniLM-L6-v2"),
                device=model_config.get("device", "cpu")
            )
        except ImportError:
            return LegacyEmbeddingBridge(provider_name)
    
    # Default to bridge
    return LegacyEmbeddingBridge(provider_name)


# Export convenience functions that match old API
def get_llm(provider: Optional[str] = None) -> Any:
    """Get LLM instance using new configuration."""
    return configure_llm_from_new_config(provider)


def get_embed_model(provider: Optional[str] = None) -> Any:
    """Get embedding model using new configuration."""
    return configure_embedding_from_new_config(provider)


# Monkey-patch the existing provider modules if they exist
try:
    # Replace old provider configuration with new one
    import app.llm.provider as old_llm_provider
    old_llm_provider.configure_llm = configure_llm_from_new_config
except ImportError:
    pass

try:
    import app.embeddings.provider as old_embed_provider
    old_embed_provider.configure_embeddings = configure_embedding_from_new_config
except ImportError:
    pass