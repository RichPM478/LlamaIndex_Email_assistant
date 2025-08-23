"""Google Gemini 2.5 model provider adapter."""
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, List
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
from dataclasses import dataclass

from src.core.application.interfaces.model_provider import (
    IModelProvider,
    IEmbeddingProvider,
    ModelConfig,
    ModelResponse,
    EmbeddingResponse
)


@dataclass
class GeminiConfig(ModelConfig):
    """Extended configuration for Gemini models."""
    safety_settings: Optional[Dict[str, str]] = None
    generation_config: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        super().__post_init__()
        # Default to Gemini 2.0 Flash
        if not self.model_name:
            self.model_name = "gemini-2.0-flash-exp"
        
        # Default safety settings - most permissive
        if self.safety_settings is None:
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }


class GeminiModelProvider(IModelProvider):
    """Google Gemini model provider implementation."""
    
    def __init__(self):
        self.model = None
        self.config: Optional[GeminiConfig] = None
        self._initialized = False
    
    async def initialize(self, config: ModelConfig) -> None:
        """Initialize Gemini with API key and settings."""
        if isinstance(config, dict):
            config = GeminiConfig(**config)
        elif not isinstance(config, GeminiConfig):
            config = GeminiConfig(
                provider=config.provider,
                model_name=config.model_name,
                api_key=config.api_key,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                extra_params=config.extra_params
            )
        
        self.config = config
        
        # Configure API key
        api_key = config.api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not provided")
        
        genai.configure(api_key=api_key)
        
        # Create model instance
        generation_config = config.generation_config or {
            "temperature": config.temperature,
            "max_output_tokens": config.max_tokens,
            "top_p": config.extra_params.get("top_p", 0.95),
            "top_k": config.extra_params.get("top_k", 40),
        }
        
        self.model = genai.GenerativeModel(
            model_name=config.model_name,
            generation_config=generation_config,
            safety_settings=config.safety_settings
        )
        
        self._initialized = True
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate text using Gemini."""
        if not self._initialized:
            raise RuntimeError("Provider not initialized")
        
        # Combine system prompt and user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        # Override generation config if needed
        generation_config = kwargs.get("generation_config", {})
        if "temperature" in kwargs:
            generation_config["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            generation_config["max_output_tokens"] = kwargs["max_tokens"]
        
        try:
            # Generate response
            response = await asyncio.to_thread(
                self.model.generate_content,
                full_prompt,
                generation_config=generation_config if generation_config else None
            )
            
            # Extract usage information
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
                "total_tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
            }
            
            return ModelResponse(
                content=response.text,
                model=self.config.model_name,
                usage=usage,
                metadata={
                    "finish_reason": response.candidates[0].finish_reason.name if response.candidates else "STOP",
                    "safety_ratings": [
                        {
                            "category": rating.category.name,
                            "probability": rating.probability.name
                        }
                        for rating in response.candidates[0].safety_ratings
                    ] if response.candidates and response.candidates[0].safety_ratings else []
                }
            )
        except Exception as e:
            raise RuntimeError(f"Gemini generation failed: {str(e)}")
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream text generation from Gemini."""
        if not self._initialized:
            raise RuntimeError("Provider not initialized")
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        try:
            # Generate streaming response
            response = await asyncio.to_thread(
                self.model.generate_content,
                full_prompt,
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            raise RuntimeError(f"Gemini streaming failed: {str(e)}")
    
    async def get_info(self) -> Dict[str, Any]:
        """Get information about the Gemini provider."""
        return {
            "provider": "gemini",
            "model": self.config.model_name if self.config else "gemini-2.0-flash-exp",
            "initialized": self._initialized,
            "supports_streaming": True,
            "supports_function_calling": True,
            "supports_vision": True,
            "max_tokens": 8192,
            "context_window": 1048576,  # 1M tokens for Gemini 2.0
            "features": [
                "text_generation",
                "code_generation",
                "function_calling",
                "vision",
                "long_context"
            ]
        }
    
    async def health_check(self) -> bool:
        """Check if Gemini API is accessible."""
        if not self._initialized:
            return False
        
        try:
            # Simple test generation
            response = await self.generate("Hello", max_tokens=5)
            return bool(response.content)
        except Exception:
            return False
    
    @property
    def supports_streaming(self) -> bool:
        """Gemini supports streaming."""
        return True
    
    @property
    def supports_function_calling(self) -> bool:
        """Gemini supports function calling."""
        return True


class GeminiEmbeddingProvider(IEmbeddingProvider):
    """Google Gemini embedding provider implementation."""
    
    def __init__(self):
        self.model = None
        self.config: Optional[GeminiConfig] = None
        self._initialized = False
        self._dimensions = 768  # Default for text-embedding-004
    
    async def initialize(self, config: ModelConfig) -> None:
        """Initialize Gemini embeddings."""
        if isinstance(config, dict):
            config = GeminiConfig(**config)
        elif not isinstance(config, GeminiConfig):
            config = GeminiConfig(
                provider=config.provider,
                model_name=config.model_name or "text-embedding-004",
                api_key=config.api_key,
                extra_params=config.extra_params
            )
        
        self.config = config
        
        # Configure API key
        api_key = config.api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not provided")
        
        genai.configure(api_key=api_key)
        
        # Set dimensions based on model
        if "text-embedding-004" in config.model_name:
            self._dimensions = 768
        elif "textembedding-gecko" in config.model_name:
            self._dimensions = 768
        
        self._initialized = True
    
    async def embed(self, text: str) -> EmbeddingResponse:
        """Generate embeddings for text."""
        if not self._initialized:
            raise RuntimeError("Provider not initialized")
        
        try:
            # Generate embedding
            result = await asyncio.to_thread(
                genai.embed_content,
                model=f"models/{self.config.model_name}",
                content=text,
                task_type="retrieval_document"
            )
            
            return EmbeddingResponse(
                embeddings=result['embedding'],
                model=self.config.model_name,
                dimensions=self._dimensions,
                usage={
                    "prompt_tokens": len(text.split()),  # Approximate
                    "total_tokens": len(text.split())
                }
            )
        except Exception as e:
            raise RuntimeError(f"Gemini embedding failed: {str(e)}")
    
    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[EmbeddingResponse]:
        """Generate embeddings for multiple texts."""
        if not self._initialized:
            raise RuntimeError("Provider not initialized")
        
        responses = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            
            try:
                # Gemini supports batch embedding
                result = await asyncio.to_thread(
                    genai.embed_content,
                    model=f"models/{self.config.model_name}",
                    content=batch,
                    task_type="retrieval_document"
                )
                
                # Create response for each embedding
                for j, embedding in enumerate(result['embedding']):
                    responses.append(EmbeddingResponse(
                        embeddings=embedding,
                        model=self.config.model_name,
                        dimensions=self._dimensions,
                        usage={
                            "prompt_tokens": len(batch[j].split()),
                            "total_tokens": len(batch[j].split())
                        }
                    ))
            except Exception as e:
                raise RuntimeError(f"Gemini batch embedding failed: {str(e)}")
        
        return responses
    
    async def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        return self._dimensions
    
    async def health_check(self) -> bool:
        """Check if Gemini embedding API is accessible."""
        if not self._initialized:
            return False
        
        try:
            response = await self.embed("test")
            return len(response.embeddings) == self._dimensions
        except Exception:
            return False