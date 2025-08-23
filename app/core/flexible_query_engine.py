"""
Flexible Query Engine
Uses the flexible architecture to enable runtime model switching and experimentation
"""
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

from .flexible_architecture import (
    FlexibleVectorStore, FlexibleEmbeddingEngine, FlexibleReranker,
    ExperimentManager, ExperimentConfig, RetrievalStrategy,
    PREDEFINED_EXPERIMENTS
)

logger = logging.getLogger(__name__)

class FlexibleQueryEngine:
    """
    Query engine that supports runtime configuration switching
    """
    
    def __init__(self, 
                 vector_store_path: str = "data/flexible_index",
                 experiments_path: str = "data/experiments"):
        
        self.vector_store = FlexibleVectorStore(Path(vector_store_path))
        self.embedding_engine = FlexibleEmbeddingEngine()
        self.reranker = FlexibleReranker()
        self.experiment_manager = ExperimentManager(Path(experiments_path))
        
        # Initialize with predefined experiments
        for name, config in PREDEFINED_EXPERIMENTS.items():
            if name not in self.experiment_manager.configs:
                self.experiment_manager.add_experiment(config)
        
        # Current configuration
        self.current_config: Optional[ExperimentConfig] = None
        self._bm25_searcher = None
        
        # Cache
        self._vectors_loaded = False
        
    def load_experiment(self, experiment_name: str) -> bool:
        """Load and configure system for specific experiment"""
        
        config = self.experiment_manager.get_experiment(experiment_name)
        if not config:
            logger.error(f"Experiment '{experiment_name}' not found")
            return False
        
        try:
            # Load embedding model
            self.embedding_engine.load_model(config.embedding_model)
            
            # Load reranker
            self.reranker.load_reranker(config.retrieval.reranker)
            
            # Load vector store if not already loaded
            if not self._vectors_loaded:
                try:
                    self.vector_store.load_vectors()
                    self._vectors_loaded = True
                    logger.info("Vector store loaded successfully")
                except FileNotFoundError:
                    logger.warning("No vector store found - indexing required")
            
            # Initialize BM25 if using hybrid/BM25 retrieval
            if config.retrieval.strategy in [RetrievalStrategy.HYBRID, RetrievalStrategy.BM25_ONLY]:
                self._init_bm25()
            
            self.current_config = config
            logger.info(f"Loaded experiment: {experiment_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load experiment {experiment_name}: {e}")
            return False
    
    def _init_bm25(self):
        """Initialize BM25 searcher if needed"""
        try:
            from rank_bm25 import BM25Okapi
            import pickle
            
            bm25_file = self.vector_store.bm25_file
            if bm25_file.exists():
                with open(bm25_file, 'rb') as f:
                    self._bm25_searcher = pickle.load(f)
                logger.info("BM25 index loaded")
            else:
                logger.warning("BM25 index not found - will be created during indexing")
        except ImportError:
            logger.warning("rank_bm25 not installed - BM25 search unavailable")
    
    def query(self, 
              query_text: str, 
              experiment_name: Optional[str] = None,
              top_k: Optional[int] = None,
              override_config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute query with specified or current experiment configuration
        """
        
        start_time = time.time()
        
        # Load experiment if specified
        if experiment_name and experiment_name != getattr(self.current_config, 'name', None):
            if not self.load_experiment(experiment_name):
                return {
                    'error': f"Failed to load experiment: {experiment_name}",
                    'query_time': time.time() - start_time
                }
        
        if not self.current_config:
            return {
                'error': "No experiment configuration loaded",
                'query_time': time.time() - start_time
            }
        
        # Use provided top_k or config default
        effective_top_k = top_k or self.current_config.retrieval.top_k
        
        try:
            # Step 1: Encode query
            query_start = time.time()
            query_vector = self.embedding_engine.encode(query_text)
            if query_vector.ndim == 2:
                query_vector = query_vector[0]  # Remove batch dimension
            query_time = time.time() - query_start
            
            # Step 2: Retrieve candidates
            retrieval_start = time.time()
            candidates = self._retrieve_candidates(
                query_text, 
                query_vector, 
                effective_top_k * 2  # Get more candidates for reranking
            )
            retrieval_time = time.time() - retrieval_start
            
            # Step 3: Rerank if configured
            rerank_start = time.time()
            if self.current_config.retrieval.reranker.value != "none":
                final_results = self.reranker.rerank(
                    query_text, 
                    candidates, 
                    self.current_config.retrieval.reranker_top_k or effective_top_k
                )
            else:
                final_results = candidates[:effective_top_k]
            rerank_time = time.time() - rerank_start
            
            # Step 4: Format results
            formatted_results = self._format_results(final_results)
            
            total_time = time.time() - start_time
            
            return {
                'results': formatted_results,
                'query': query_text,
                'experiment': self.current_config.name,
                'total_candidates': len(candidates),
                'final_results': len(final_results),
                'timing': {
                    'query_encoding': query_time,
                    'retrieval': retrieval_time,
                    'reranking': rerank_time,
                    'total': total_time
                },
                'config': {
                    'embedding_model': self.current_config.embedding_model.model_name,
                    'retrieval_strategy': self.current_config.retrieval.strategy.value,
                    'reranker': self.current_config.retrieval.reranker.value
                }
            }
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {
                'error': str(e),
                'query_time': time.time() - start_time
            }
    
    def _retrieve_candidates(self, 
                           query_text: str, 
                           query_vector, 
                           top_k: int) -> List[Dict]:
        """Retrieve candidate documents based on strategy"""
        
        strategy = self.current_config.retrieval.strategy
        
        if strategy == RetrievalStrategy.VECTOR_ONLY:
            return self.vector_store.search(
                query_vector, 
                top_k=top_k,
                threshold=self.current_config.retrieval.similarity_threshold
            )
        
        elif strategy == RetrievalStrategy.BM25_ONLY:
            return self._bm25_search(query_text, top_k)
        
        elif strategy == RetrievalStrategy.HYBRID:
            return self._hybrid_search(query_text, query_vector, top_k)
        
        elif strategy == RetrievalStrategy.ENSEMBLE:
            return self._ensemble_search(query_text, query_vector, top_k)
        
        else:
            raise ValueError(f"Unknown retrieval strategy: {strategy}")
    
    def _bm25_search(self, query_text: str, top_k: int) -> List[Dict]:
        """BM25-only search"""
        if not self._bm25_searcher:
            logger.warning("BM25 searcher not available")
            return []
        
        # Tokenize query (simple split for now)
        query_tokens = query_text.lower().split()
        scores = self._bm25_searcher.get_scores(query_tokens)
        
        # Get top-k results
        import numpy as np
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include positive scores
                results.append({
                    'document': self.vector_store._documents[idx],
                    'score': float(scores[idx]),
                    'index': int(idx),
                    'type': 'bm25'
                })
        
        return results
    
    def _hybrid_search(self, query_text: str, query_vector, top_k: int) -> List[Dict]:
        """Hybrid vector + BM25 search"""
        
        # Get vector results
        vector_results = self.vector_store.search(query_vector, top_k=top_k)
        
        # Get BM25 results
        bm25_results = self._bm25_search(query_text, top_k)
        
        # Combine and reweight
        vector_weight = self.current_config.retrieval.vector_weight
        bm25_weight = self.current_config.retrieval.bm25_weight
        
        # Normalize scores
        if vector_results:
            max_vector_score = max(r['score'] for r in vector_results)
            for r in vector_results:
                r['normalized_score'] = r['score'] / max_vector_score
        
        if bm25_results:
            max_bm25_score = max(r['score'] for r in bm25_results)
            for r in bm25_results:
                r['normalized_score'] = r['score'] / max_bm25_score
        
        # Combine scores
        combined = {}
        
        for result in vector_results:
            doc_id = result['index']
            combined[doc_id] = {
                'document': result['document'],
                'vector_score': result['normalized_score'] * vector_weight,
                'bm25_score': 0,
                'combined_score': result['normalized_score'] * vector_weight,
                'index': doc_id
            }
        
        for result in bm25_results:
            doc_id = result['index']
            if doc_id in combined:
                combined[doc_id]['bm25_score'] = result['normalized_score'] * bm25_weight
                combined[doc_id]['combined_score'] += result['normalized_score'] * bm25_weight
            else:
                combined[doc_id] = {
                    'document': result['document'],
                    'vector_score': 0,
                    'bm25_score': result['normalized_score'] * bm25_weight,
                    'combined_score': result['normalized_score'] * bm25_weight,
                    'index': doc_id
                }
        
        # Sort by combined score and return top-k
        sorted_results = sorted(combined.values(), 
                              key=lambda x: x['combined_score'], 
                              reverse=True)
        
        # Format for consistency
        formatted_results = []
        for r in sorted_results[:top_k]:
            formatted_results.append({
                'document': r['document'],
                'score': r['combined_score'],
                'index': r['index'],
                'type': 'hybrid',
                'vector_score': r['vector_score'],
                'bm25_score': r['bm25_score']
            })
        
        return formatted_results
    
    def _ensemble_search(self, query_text: str, query_vector, top_k: int) -> List[Dict]:
        """Ensemble search (placeholder for advanced methods)"""
        # For now, use hybrid search
        return self._hybrid_search(query_text, query_vector, top_k)
    
    def _format_results(self, results: List[Dict]) -> List[Dict]:
        """Format results for consistent output"""
        
        formatted = []
        for result in results:
            doc = result['document']
            
            # Extract key information from document
            formatted_doc = {
                'content': doc.get('content', ''),
                'metadata': doc.get('metadata', {}),
                'score': result.get('score', 0),
                'rerank_score': result.get('rerank_score'),
                'retrieval_type': result.get('type', 'vector'),
            }
            
            # Add email-specific fields if available
            metadata = doc.get('metadata', {})
            if 'subject' in metadata:
                formatted_doc['subject'] = metadata['subject']
            if 'from' in metadata:
                formatted_doc['from'] = metadata['from']
            if 'date' in metadata:
                formatted_doc['date'] = metadata['date']
            
            formatted.append(formatted_doc)
        
        return formatted
    
    def benchmark_experiments(self, 
                            queries: List[str], 
                            experiment_names: Optional[List[str]] = None) -> Dict[str, Dict]:
        """
        Benchmark multiple experiments against a set of queries
        """
        
        if experiment_names is None:
            experiment_names = self.experiment_manager.list_experiments()
        
        results = {}
        
        for exp_name in experiment_names:
            logger.info(f"Benchmarking experiment: {exp_name}")
            
            exp_results = {
                'queries': [],
                'avg_retrieval_time': 0,
                'avg_total_time': 0,
                'total_results': 0
            }
            
            total_retrieval_time = 0
            total_time = 0
            
            for query in queries:
                result = self.query(query, experiment_name=exp_name)
                
                if 'error' not in result:
                    exp_results['queries'].append({
                        'query': query,
                        'results_count': len(result['results']),
                        'timing': result['timing']
                    })
                    
                    total_retrieval_time += result['timing']['retrieval']
                    total_time += result['timing']['total']
                    exp_results['total_results'] += len(result['results'])
            
            # Calculate averages
            if exp_results['queries']:
                exp_results['avg_retrieval_time'] = total_retrieval_time / len(exp_results['queries'])
                exp_results['avg_total_time'] = total_time / len(exp_results['queries'])
            
            results[exp_name] = exp_results
        
        return results
    
    def get_current_config(self) -> Optional[ExperimentConfig]:
        """Get currently loaded configuration"""
        return self.current_config
    
    def list_experiments(self) -> List[str]:
        """List available experiments"""
        return self.experiment_manager.list_experiments()