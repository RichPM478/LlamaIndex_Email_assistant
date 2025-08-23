"""Model provider interface - defines contract for all LLM/embedding providers."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum


class ModelType(Enum):
    """Types of models supported."""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    RERANKING = "reranking"


@dataclass
class ModelConfig:
    """Configuration for a model provider."""
    model_name: str
    provider: Optional[str] = None
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 30
    extra_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}


@dataclass
class ModelResponse:
    """Standard response from model providers."""
    content: str
    model: str
    usage: Dict[str, int]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class EmbeddingResponse:
    """Response from embedding models."""
    embeddings: List[float]
    model: str
    dimensions: int
    usage: Dict[str, int]


class IModelProvider(ABC):
    """Interface for language model providers."""
    
    @abstractmethod
    async def initialize(self, config: ModelConfig) -> None:
        """Initialize the provider with configuration."""
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate text from the model."""
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream text generation from the model."""
        pass
    
    @abstractmethod
    async def get_info(self) -> Dict[str, Any]:
        """Get information about the provider and model."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy and accessible."""
        pass
    
    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Check if provider supports streaming."""
        pass
    
    @property
    @abstractmethod
    def supports_function_calling(self) -> bool:
        """Check if provider supports function calling."""
        pass


class IEmbeddingProvider(ABC):
    """Interface for embedding model providers."""
    
    @abstractmethod
    async def initialize(self, config: ModelConfig) -> None:
        """Initialize the embedding provider."""
        pass
    
    @abstractmethod
    async def embed(self, text: str) -> EmbeddingResponse:
        """Generate embeddings for text."""
        pass
    
    @abstractmethod
    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[EmbeddingResponse]:
        """Generate embeddings for multiple texts."""
        pass
    
    @abstractmethod
    async def get_dimensions(self) -> int:
        """Get the dimensionality of embeddings."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy."""
        pass


class IRerankerProvider(ABC):
    """Interface for reranking model providers."""
    
    @abstractmethod
    async def initialize(self, config: ModelConfig) -> None:
        """Initialize the reranker provider."""
        pass
    
    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 10
    ) -> List[tuple[int, float]]:
        """
        Rerank documents based on relevance to query.
        Returns list of (index, score) tuples.
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy."""
        pass