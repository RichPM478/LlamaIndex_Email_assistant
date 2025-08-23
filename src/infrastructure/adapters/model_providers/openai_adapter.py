"""OpenAI model provider adapter."""
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, List
from openai import AsyncOpenAI, OpenAI
import os

from src.core.application.interfaces.model_provider import (
    IModelProvider,
    IEmbeddingProvider,
    ModelConfig,
    ModelResponse,
    EmbeddingResponse
)


class OpenAIModelProvider(IModelProvider):
    """OpenAI model provider implementation."""
    
    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.sync_client: Optional[OpenAI] = None
        self.config: Optional[ModelConfig] = None
        self._initialized = False
    
    async def initialize(self, config: ModelConfig) -> None:
        """Initialize OpenAI client."""
        self.config = config
        
        # Get API key
        api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not provided")
        
        # Initialize clients
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=config.endpoint if config.endpoint else None,
            timeout=config.timeout
        )
        self.sync_client = OpenAI(
            api_key=api_key,
            base_url=config.endpoint if config.endpoint else None,
            timeout=config.timeout
        )
        
        self._initialized = True
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate text using OpenAI."""
        if not self._initialized:
            raise RuntimeError("Provider not initialized")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Merge kwargs with config
        temperature = kwargs.get("temperature", self.config.temperature)
        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model_name or "gpt-4-turbo-preview",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **{k: v for k, v in kwargs.items() 
                   if k not in ["temperature", "max_tokens"]}
            )
            
            return ModelResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "id": response.id
                }
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI generation failed: {str(e)}")
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream text generation from OpenAI."""
        if not self._initialized:
            raise RuntimeError("Provider not initialized")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.config.model_name or "gpt-4-turbo-preview",
                messages=messages,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise RuntimeError(f"OpenAI streaming failed: {str(e)}")
    
    async def get_info(self) -> Dict[str, Any]:
        """Get information about the OpenAI provider."""
        return {
            "provider": "openai",
            "model": self.config.model_name if self.config else "gpt-4-turbo-preview",
            "initialized": self._initialized,
            "supports_streaming": True,
            "supports_function_calling": True,
            "supports_vision": "vision" in (self.config.model_name or ""),
            "max_tokens": 128000 if "gpt-4" in (self.config.model_name or "gpt-4") else 16384,
            "features": [
                "text_generation",
                "code_generation",
                "function_calling",
                "json_mode"
            ]
        }
    
    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        if not self._initialized:
            return False
        
        try:
            response = await self.generate("Hello", max_tokens=5)
            return bool(response.content)
        except Exception:
            return False
    
    @property
    def supports_streaming(self) -> bool:
        return True
    
    @property
    def supports_function_calling(self) -> bool:
        return True


class OpenAIEmbeddingProvider(IEmbeddingProvider):
    """OpenAI embedding provider implementation."""
    
    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.config: Optional[ModelConfig] = None
        self._initialized = False
        self._dimensions = 1536  # Default for text-embedding-ada-002
    
    async def initialize(self, config: ModelConfig) -> None:
        """Initialize OpenAI embeddings."""
        self.config = config
        
        api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not provided")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=config.endpoint if config.endpoint else None,
            timeout=config.timeout
        )
        
        # Set dimensions based on model
        model_name = config.model_name or "text-embedding-3-small"
        if "text-embedding-3-large" in model_name:
            self._dimensions = 3072
        elif "text-embedding-3-small" in model_name:
            self._dimensions = 1536
        elif "text-embedding-ada-002" in model_name:
            self._dimensions = 1536
        
        self._initialized = True
    
    async def embed(self, text: str) -> EmbeddingResponse:
        """Generate embeddings for text."""
        if not self._initialized:
            raise RuntimeError("Provider not initialized")
        
        try:
            response = await self.client.embeddings.create(
                model=self.config.model_name or "text-embedding-3-small",
                input=text
            )
            
            return EmbeddingResponse(
                embeddings=response.data[0].embedding,
                model=response.model,
                dimensions=self._dimensions,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI embedding failed: {str(e)}")
    
    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[EmbeddingResponse]:
        """Generate embeddings for multiple texts."""
        if not self._initialized:
            raise RuntimeError("Provider not initialized")
        
        responses = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            
            try:
                response = await self.client.embeddings.create(
                    model=self.config.model_name or "text-embedding-3-small",
                    input=batch
                )
                
                for j, data in enumerate(response.data):
                    responses.append(EmbeddingResponse(
                        embeddings=data.embedding,
                        model=response.model,
                        dimensions=self._dimensions,
                        usage={
                            "prompt_tokens": response.usage.prompt_tokens // len(batch),
                            "total_tokens": response.usage.total_tokens // len(batch)
                        }
                    ))
            except Exception as e:
                raise RuntimeError(f"OpenAI batch embedding failed: {str(e)}")
        
        return responses
    
    async def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        return self._dimensions
    
    async def health_check(self) -> bool:
        """Check if OpenAI embedding API is accessible."""
        if not self._initialized:
            return False
        
        try:
            response = await self.embed("test")
            return len(response.embeddings) == self._dimensions
        except Exception:
            return False