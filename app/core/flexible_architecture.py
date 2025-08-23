"""
Flexible Email Intelligence Architecture
Enables easy experimentation with different models, rerankers, and pipelines
"""
import json
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Protocol
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuration Enums
class EmbeddingProvider(Enum):
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    MIXEDBREAD = "mixedbread"
    GEMINI = "gemini"
    COHERE = "cohere"

class RerankerType(Enum):
    NONE = "none"
    CROSS_ENCODER = "cross_encoder"
    COLBERT = "colbert"
    COHERE = "cohere_rerank"
    BGE_RERANKER = "bge_reranker"

class RetrievalStrategy(Enum):
    VECTOR_ONLY = "vector_only"
    BM25_ONLY = "bm25_only"
    HYBRID = "hybrid"
    ENSEMBLE = "ensemble"

@dataclass
class ModelConfig:
    """Configuration for embedding models"""
    provider: EmbeddingProvider
    model_name: str
    dimensions: int
    max_tokens: Optional[int] = None
    device: str = "auto"
    batch_size: int = 64
    normalize: bool = True
    extra_params: Dict[str, Any] = None

@dataclass
class RetrievalConfig:
    """Configuration for retrieval pipeline"""
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    top_k: int = 10
    reranker: RerankerType = RerankerType.CROSS_ENCODER
    reranker_top_k: int = 5
    vector_weight: float = 0.7
    bm25_weight: float = 0.3
    similarity_threshold: float = 0.0
    extra_params: Dict[str, Any] = None

@dataclass
class ExperimentConfig:
    """Complete experiment configuration"""
    name: str
    description: str
    embedding_model: ModelConfig
    retrieval: RetrievalConfig
    created_at: str
    version: str = "1.0"

class FlexibleVectorStore:
    """
    Model-agnostic vector store that separates vectors from model configuration
    """
    
    def __init__(self, store_path: Path):
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        
        # Core data files
        self.vectors_file = self.store_path / "vectors.npy"
        self.metadata_file = self.store_path / "metadata.json"
        self.documents_file = self.store_path / "documents.pkl"
        self.config_file = self.store_path / "build_config.json"
        self.bm25_file = self.store_path / "bm25_index.pkl"
        
        # Runtime state
        self._vectors: Optional[np.ndarray] = None
        self._metadata: Optional[Dict] = None
        self._documents: Optional[List[Dict]] = None
        self._build_config: Optional[ModelConfig] = None
        self._bm25_index = None
        
    def save_vectors(self, vectors: np.ndarray, metadata: Dict, documents: List[Dict], 
                    build_config: ModelConfig):
        """Save vectors with metadata (model-agnostic)"""
        
        # Save vectors as numpy array
        np.save(self.vectors_file, vectors)
        
        # Save metadata (includes document IDs, email info, etc.)
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Save full documents for retrieval
        with open(self.documents_file, 'wb') as f:
            pickle.dump(documents, f)
        
        # Save build configuration for compatibility checking
        config_dict = asdict(build_config)
        # Convert enum to string for JSON serialization
        config_dict['provider'] = config_dict['provider'].value
        with open(self.config_file, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        logger.info(f"Saved {len(vectors)} vectors to {self.store_path}")
    
    def load_vectors(self) -> tuple[np.ndarray, Dict, List[Dict], ModelConfig]:
        """Load vectors and metadata"""
        
        if not all([f.exists() for f in [self.vectors_file, self.metadata_file, 
                                       self.documents_file, self.config_file]]):
            raise FileNotFoundError(f"Vector store not found at {self.store_path}")
        
        # Load vectors
        vectors = np.load(self.vectors_file)
        
        # Load metadata
        with open(self.metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Load documents
        with open(self.documents_file, 'rb') as f:
            documents = pickle.load(f)
        
        # Load build config
        with open(self.config_file, 'r') as f:
            config_dict = json.load(f)
            # Convert provider string back to enum
            config_dict['provider'] = EmbeddingProvider(config_dict['provider'])
            build_config = ModelConfig(**config_dict)
        
        self._vectors = vectors
        self._metadata = metadata
        self._documents = documents
        self._build_config = build_config
        
        return vectors, metadata, documents, build_config
    
    def search(self, query_vector: np.ndarray, top_k: int = 10, 
               threshold: float = 0.0) -> List[Dict]:
        """Vector similarity search"""
        if self._vectors is None:
            self.load_vectors()
        
        # Cosine similarity
        similarities = np.dot(self._vectors, query_vector) / (
            np.linalg.norm(self._vectors, axis=1) * np.linalg.norm(query_vector)
        )
        
        # Get top-k results above threshold
        indices = np.argsort(similarities)[::-1]
        results = []
        
        for idx in indices[:top_k]:
            if similarities[idx] >= threshold:
                results.append({
                    'document': self._documents[idx],
                    'score': float(similarities[idx]),
                    'index': int(idx)
                })
        
        return results

class FlexibleEmbeddingEngine:
    """
    Runtime embedding model that can switch between providers
    """
    
    def __init__(self):
        self._current_model = None
        self._current_config = None
        
    def load_model(self, config: ModelConfig):
        """Load embedding model based on configuration"""
        
        if config.provider == EmbeddingProvider.HUGGINGFACE:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(config.model_name, device=config.device)
            self._current_model = model
            
        elif config.provider == EmbeddingProvider.OPENAI:
            from openai import OpenAI
            import os
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self._current_model = client
            
        elif config.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
            # Alias for HuggingFace
            return self.load_model(ModelConfig(
                provider=EmbeddingProvider.HUGGINGFACE,
                model_name=config.model_name,
                dimensions=config.dimensions,
                device=config.device,
                batch_size=config.batch_size
            ))
            
        elif config.provider == EmbeddingProvider.MIXEDBREAD:
            # Use HuggingFace with mixedbread model
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("mixedbread-ai/mxbai-embed-large-v1", device=config.device)
            self._current_model = model
            # Keep original MIXEDBREAD provider type for encode method
            self._current_config = config
        
        else:
            raise ValueError(f"Unsupported embedding provider: {config.provider}")
        
        # Set current config (may have been updated for MIXEDBREAD)
        if not hasattr(self, '_current_config') or self._current_config is None:
            self._current_config = config
        
        logger.info(f"Loaded {config.provider.value} model: {config.model_name}")
    
    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """Encode texts to vectors"""
        if self._current_model is None:
            raise RuntimeError("No embedding model loaded")
        
        if isinstance(texts, str):
            texts = [texts]
        
        if self._current_config.provider in [EmbeddingProvider.HUGGINGFACE, EmbeddingProvider.MIXEDBREAD]:
            vectors = self._current_model.encode(
                texts, 
                batch_size=self._current_config.batch_size,
                normalize_embeddings=self._current_config.normalize,
                show_progress_bar=len(texts) > 100
            )
            return vectors
        
        elif self._current_config.provider == EmbeddingProvider.OPENAI:
            # OpenAI API call
            response = self._current_model.embeddings.create(
                model=self._current_config.model_name,
                input=texts
            )
            vectors = np.array([item.embedding for item in response.data])
            return vectors
        
        else:
            raise ValueError(f"Encoding not implemented for {self._current_config.provider}")

class FlexibleReranker:
    """
    Pluggable reranking system
    """
    
    def __init__(self):
        self._current_reranker = None
        self._current_type = None
    
    def load_reranker(self, reranker_type: RerankerType, model_name: str = None):
        """Load reranker based on type"""
        
        if reranker_type == RerankerType.NONE:
            self._current_reranker = None
            
        elif reranker_type == RerankerType.CROSS_ENCODER:
            from sentence_transformers import CrossEncoder
            model_name = model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2"
            self._current_reranker = CrossEncoder(model_name)
            
        elif reranker_type == RerankerType.BGE_RERANKER:
            from sentence_transformers import CrossEncoder
            model_name = model_name or "BAAI/bge-reranker-base"
            self._current_reranker = CrossEncoder(model_name)
            
        else:
            raise ValueError(f"Unsupported reranker: {reranker_type}")
        
        self._current_type = reranker_type
        logger.info(f"Loaded reranker: {reranker_type.value}")
    
    def rerank(self, query: str, documents: List[Dict], top_k: int = 5) -> List[Dict]:
        """Rerank documents based on query"""
        
        if self._current_reranker is None or len(documents) <= top_k:
            return documents[:top_k]
        
        # Prepare query-document pairs
        pairs = [(query, doc['document'].get('content', '')) for doc in documents]
        
        # Get reranking scores
        scores = self._current_reranker.predict(pairs)
        
        # Add rerank scores and sort
        for i, doc in enumerate(documents):
            doc['rerank_score'] = float(scores[i])
            doc['original_rank'] = i
        
        # Sort by rerank score and return top-k
        reranked = sorted(documents, key=lambda x: x['rerank_score'], reverse=True)
        return reranked[:top_k]

class ExperimentManager:
    """
    Manages different experimental configurations and results
    """
    
    def __init__(self, experiments_path: Path):
        self.experiments_path = Path(experiments_path)
        self.experiments_path.mkdir(parents=True, exist_ok=True)
        
        self.configs_file = self.experiments_path / "configs.json"
        self.results_file = self.experiments_path / "results.json"
        
        # Load existing configs
        self.configs = self._load_configs()
        self.results = self._load_results()
    
    def _load_configs(self) -> Dict[str, ExperimentConfig]:
        """Load experiment configurations"""
        if not self.configs_file.exists():
            return {}
        
        with open(self.configs_file, 'r') as f:
            data = json.load(f)
        
        configs = {}
        for name, config_dict in data.items():
            # Reconstruct nested objects with enum conversion
            embed_dict = config_dict['embedding_model'].copy()
            # Convert provider string back to enum
            provider_str = embed_dict['provider']
            if provider_str.startswith('EmbeddingProvider.'):
                embed_dict['provider'] = EmbeddingProvider(provider_str.split('.')[1].lower())
            
            retrieval_dict = config_dict['retrieval'].copy()
            # Convert strategy and reranker strings back to enums
            strategy_str = retrieval_dict['strategy']
            if strategy_str.startswith('RetrievalStrategy.'):
                retrieval_dict['strategy'] = RetrievalStrategy(strategy_str.split('.')[1].lower())
            
            reranker_str = retrieval_dict['reranker']
            if reranker_str.startswith('RerankerType.'):
                retrieval_dict['reranker'] = RerankerType(reranker_str.split('.')[1].lower())
            
            embedding_config = ModelConfig(**embed_dict)
            retrieval_config = RetrievalConfig(**retrieval_dict)
            
            config_dict['embedding_model'] = embedding_config
            config_dict['retrieval'] = retrieval_config
            
            configs[name] = ExperimentConfig(**config_dict)
        
        return configs
    
    def _load_results(self) -> Dict[str, Dict]:
        """Load experiment results"""
        if not self.results_file.exists():
            return {}
        
        with open(self.results_file, 'r') as f:
            return json.load(f)
    
    def save_configs(self):
        """Save configurations to disk"""
        data = {}
        for name, config in self.configs.items():
            config_dict = asdict(config)
            data[name] = config_dict
        
        with open(self.configs_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def add_experiment(self, config: ExperimentConfig):
        """Add new experiment configuration"""
        self.configs[config.name] = config
        self.save_configs()
        logger.info(f"Added experiment: {config.name}")
    
    def get_experiment(self, name: str) -> Optional[ExperimentConfig]:
        """Get experiment configuration by name"""
        return self.configs.get(name)
    
    def list_experiments(self) -> List[str]:
        """List all experiment names"""
        return list(self.configs.keys())
    
    def record_result(self, experiment_name: str, metrics: Dict[str, float]):
        """Record experiment results"""
        if experiment_name not in self.results:
            self.results[experiment_name] = []
        
        result = {
            'timestamp': str(datetime.now()),
            'metrics': metrics
        }
        
        self.results[experiment_name].append(result)
        
        with open(self.results_file, 'w') as f:
            json.dump(self.results, f, indent=2)

# Predefined experiment configurations
PREDEFINED_EXPERIMENTS = {
    "mixedbread_hybrid": ExperimentConfig(
        name="mixedbread_hybrid",
        description="Mixedbread embeddings with hybrid retrieval and cross-encoder reranking",
        embedding_model=ModelConfig(
            provider=EmbeddingProvider.MIXEDBREAD,
            model_name="mixedbread-ai/mxbai-embed-large-v1",
            dimensions=1024,
            device="cuda",
            batch_size=64
        ),
        retrieval=RetrievalConfig(
            strategy=RetrievalStrategy.HYBRID,
            reranker=RerankerType.CROSS_ENCODER,
            vector_weight=0.7,
            bm25_weight=0.3,
            top_k=10,
            reranker_top_k=5
        ),
        created_at=str(datetime.now())
    ),
    
    "openai_vector_only": ExperimentConfig(
        name="openai_vector_only",
        description="OpenAI embeddings with vector-only retrieval",
        embedding_model=ModelConfig(
            provider=EmbeddingProvider.OPENAI,
            model_name="text-embedding-3-large",
            dimensions=3072,
            device="cpu",
            batch_size=100
        ),
        retrieval=RetrievalConfig(
            strategy=RetrievalStrategy.VECTOR_ONLY,
            reranker=RerankerType.NONE,
            top_k=10
        ),
        created_at=str(datetime.now())
    ),
    
    "bge_ensemble": ExperimentConfig(
        name="bge_ensemble",
        description="BGE embeddings with ensemble retrieval and BGE reranking",
        embedding_model=ModelConfig(
            provider=EmbeddingProvider.HUGGINGFACE,
            model_name="BAAI/bge-large-en-v1.5",
            dimensions=1024,
            device="cuda",
            batch_size=32
        ),
        retrieval=RetrievalConfig(
            strategy=RetrievalStrategy.ENSEMBLE,
            reranker=RerankerType.BGE_RERANKER,
            vector_weight=0.6,
            bm25_weight=0.4,
            top_k=15,
            reranker_top_k=5
        ),
        created_at=str(datetime.now())
    )
}