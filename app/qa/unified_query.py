# app/qa/unified_query.py
"""
Unified query engine that consolidates all query functionality with configurable strategies.
Combines features from simple_query.py, query_engine.py, and optimized_query.py.
"""
from typing import Dict, Any, List, Optional
from llama_index.core import StorageContext, load_index_from_storage, VectorStoreIndex, QueryBundle
from llama_index.core.response_synthesizers import get_response_synthesizer, ResponseMode
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter, FilterOperator
from llama_index.core.schema import NodeWithScore
from app.config.settings import get_settings
from app.llm.provider import configure_llm
from app.embeddings.provider import configure_embeddings
import re
import time
from enum import Enum

class QueryStrategy(Enum):
    """Query strategy options"""
    SIMPLE = "simple"           # Simple post-filtering approach
    ADVANCED = "advanced"       # Advanced metadata filtering
    OPTIMIZED = "optimized"     # Cached models with performance optimization

class EmailQueryEngine:
    """Unified email query engine with configurable strategies"""
    
    # Global cache for models and index (from optimized_query.py)
    _cache = {
        'llm': None,
        'embed_model': None,
        'index': None,
        'last_loaded': None,
        'settings': None
    }
    
    def __init__(self, strategy: QueryStrategy = QueryStrategy.OPTIMIZED, persist_dir: str = "data/index"):
        self.strategy = strategy
        self.persist_dir = persist_dir
        
        # Load settings once
        if self._cache['settings'] is None:
            self._cache['settings'] = get_settings()
    
    def _ensure_models_loaded(self):
        """Ensure models are loaded and cached (optimized strategy)"""
        if self._cache['llm'] is None or self._cache['embed_model'] is None:
            print("[INFO] Loading models into cache...")
            s = self._cache['settings']
            self._cache['llm'] = configure_llm(s)
            self._cache['embed_model'] = configure_embeddings(s)
            print("[INFO] Models cached successfully")
        return self._cache['llm'], self._cache['embed_model']
    
    def _ensure_index_loaded(self) -> VectorStoreIndex:
        """Ensure index is loaded and cached (optimized strategy)"""
        if self._cache['index'] is None:
            print("[INFO] Loading index into cache...")
            storage_context = StorageContext.from_defaults(persist_dir=self.persist_dir)
            self._cache['index'] = load_index_from_storage(storage_context)
            self._cache['last_loaded'] = time.time()
            print("[INFO] Index cached successfully")
        return self._cache['index']
    
    def _load_models_fresh(self):
        """Load models fresh without caching (simple/advanced strategies)"""
        s = self._cache['settings']
        configure_llm(s)
        configure_embeddings(s)
    
    def _load_index_fresh(self) -> VectorStoreIndex:
        """Load index fresh without caching (simple/advanced strategies)"""
        storage_context = StorageContext.from_defaults(persist_dir=self.persist_dir)
        return load_index_from_storage(storage_context)
    
    def _extract_sender_from_query(self, query: str) -> Optional[str]:
        """
        Extract sender name from queries.
        Combines simple regex (simple_query.py) with security features (query_engine.py)
        """
        if not isinstance(query, str) or not query.strip():
            return None
        
        # Simple regex approach (from simple_query.py)
        simple_match = re.search(r"from\s+([^,\.\?]+)", query.lower())
        if simple_match:
            return simple_match.group(1).strip()
        
        # Advanced approach with security (from query_engine.py)
        if self.strategy == QueryStrategy.ADVANCED:
            try:
                from app.security.regex_utils import secure_regex
                from app.security.sanitizer import sanitizer
                
                # Sanitize the input first
                sanitized_query = sanitizer.sanitize_query_input(query)
                
                # Use secure regex patterns
                patterns = [
                    r"(?:from|sender|by)\s+([a-zA-Z0-9\s\-\.]+)",
                    r"emails?\s+from\s+([a-zA-Z0-9\s\-\.]+)",
                    r"messages?\s+from\s+([a-zA-Z0-9\s\-\.]+)"
                ]
                
                for pattern in patterns:
                    if secure_regex.is_safe_pattern(pattern):
                        match = re.search(pattern, sanitized_query, re.IGNORECASE)
                        if match:
                            sender = match.group(1).strip()
                            # Additional validation
                            if len(sender) > 2 and len(sender) < 100:
                                return sender
            except ImportError:
                # Fallback to simple approach if security modules not available
                pass
        
        return None
    
    def _simple_query(self, question: str, top_k: int = 10, **kwargs) -> Dict[str, Any]:
        """Simple query strategy (from simple_query.py)"""
        if self.strategy == QueryStrategy.OPTIMIZED:
            self._ensure_models_loaded()
            index = self._ensure_index_loaded()
        else:
            self._load_models_fresh()
            index = self._load_index_fresh()
        
        # Check for sender filtering
        target_sender = self._extract_sender_from_query(question)
        
        # Create query engine with more results if filtering by sender
        actual_top_k = top_k * 3 if target_sender else top_k
        query_engine = index.as_query_engine(
            similarity_top_k=actual_top_k,
            response_mode="compact"
        )
        
        # Execute query
        response = query_engine.query(question)
        source_nodes = getattr(response, 'source_nodes', [])
        
        # Post-filter for sender if needed
        if target_sender:
            filtered_nodes = []
            for node in source_nodes:
                from_field = node.node.metadata.get('from', '').lower()
                from_normalized = node.node.metadata.get('from_normalized', '').lower()
                
                if target_sender in from_field or target_sender in from_normalized:
                    filtered_nodes.append(node)
            
            if filtered_nodes:
                source_nodes = filtered_nodes[:top_k]
        
        # Build citations
        citations = []
        for node in source_nodes[:top_k]:
            citation = dict(node.node.metadata)
            citation['score'] = node.score if hasattr(node, 'score') else None
            citation['snippet'] = node.node.text[:200] if hasattr(node.node, 'text') else ""
            citations.append(citation)
        
        return {
            "answer": str(response),
            "confidence": getattr(response, "score", None),
            "citations": citations,
            "metadata_filters_applied": target_sender is not None,
            "strategy": "simple"
        }
    
    def _advanced_query(self, question: str, top_k: int = 5, **kwargs) -> Dict[str, Any]:
        """Advanced query strategy with metadata filtering (from query_engine.py)"""
        if self.strategy == QueryStrategy.OPTIMIZED:
            self._ensure_models_loaded()
            index = self._ensure_index_loaded()
        else:
            self._load_models_fresh()
            index = self._load_index_fresh()
        
        # Extract sender for metadata filtering
        sender_name = self._extract_sender_from_query(question)
        
        # Build metadata filters if sender specified
        filters = None
        if sender_name:
            filters = MetadataFilters(filters=[
                MetadataFilter(
                    key="from_normalized", 
                    value=sender_name.lower(), 
                    operator=FilterOperator.CONTAINS
                )
            ])
        
        # Create retriever with metadata filtering
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=top_k,
            filters=filters
        )
        
        # Get response synthesizer
        response_synthesizer = get_response_synthesizer(response_mode=ResponseMode.COMPACT)
        
        # Create query bundle
        query_bundle = QueryBundle(query_str=question)
        
        # Retrieve nodes
        nodes = retriever.retrieve(query_bundle)
        
        # Synthesize response
        response = response_synthesizer.synthesize(query_bundle, nodes)
        
        # Build citations from nodes
        citations = []
        for node in nodes:
            citation = {
                'from': node.node.metadata.get('from', 'Unknown'),
                'subject': node.node.metadata.get('subject', 'No subject'),
                'date': node.node.metadata.get('date', ''),
                'snippet': node.node.text[:200] if hasattr(node.node, 'text') else "",
                'score': node.score if hasattr(node, 'score') else None
            }
            citations.append(citation)
        
        return {
            "answer": str(response),
            "citations": citations,
            "metadata_filters_applied": sender_name is not None,
            "strategy": "advanced"
        }
    
    def _optimized_query(self, question: str, top_k: int = 5, response_mode: str = "compact", streaming: bool = False, **kwargs) -> Dict[str, Any]:
        """Optimized query strategy with caching (from optimized_query.py)"""
        start_time = time.time()
        
        # Ensure models and index are loaded
        self._ensure_models_loaded()
        index = self._ensure_index_loaded()
        
        # Check for sender-specific queries
        target_sender = self._extract_sender_from_query(question)
        
        # Adjust top_k for sender queries
        if target_sender:
            actual_top_k = min(top_k * 2, 20)  # Get more results for filtering
        else:
            actual_top_k = top_k
        
        # Create query engine with optimized settings
        query_engine = index.as_query_engine(
            similarity_top_k=actual_top_k,
            response_mode=response_mode,
            streaming=streaming,
            verbose=False  # Reduce logging overhead
        )
        
        # Execute query
        query_start = time.time()
        response = query_engine.query(question)
        query_time = time.time() - query_start
        
        # Get source nodes
        source_nodes = getattr(response, 'source_nodes', [])
        
        # Post-filter for sender if needed
        if target_sender:
            filtered_nodes = []
            for node in source_nodes:
                from_field = node.node.metadata.get('from', '').lower()
                from_normalized = node.node.metadata.get('from_normalized', '').lower()
                
                if target_sender in from_field or target_sender in from_normalized:
                    filtered_nodes.append(node)
            
            if filtered_nodes:
                source_nodes = filtered_nodes[:top_k]
        
        # Build citations with clean text
        citations = []
        for node in source_nodes[:top_k]:
            meta = dict(node.node.metadata)
            
            # Extract clean snippet from node text
            text = node.node.text if hasattr(node.node, 'text') else ""
            
            # Remove the metadata prefix from text if present
            if "From:" in text and "Subject:" in text:
                # Find the actual content after the metadata
                lines = text.split('\n')
                content_start = 0
                for i, line in enumerate(lines):
                    if line.strip() == "":
                        content_start = i + 1
                        break
                text = '\n'.join(lines[content_start:])
            
            citation = {
                'from': meta.get('from', 'Unknown'),
                'subject': meta.get('subject', 'No subject'),
                'date': meta.get('date', ''),
                'snippet': text[:300].strip(),  # Clean snippet
                'score': node.score if hasattr(node, 'score') else None
            }
            citations.append(citation)
        
        total_time = time.time() - start_time
        
        return {
            "answer": str(response),
            "citations": citations,
            "metadata": {
                "total_time": total_time,
                "query_time": query_time,
                "top_k": top_k,
                "filtered_by_sender": target_sender is not None,
                "cache_used": True,
                "strategy": "optimized"
            }
        }
    
    def query(self, question: str, **kwargs) -> Dict[str, Any]:
        """
        Main query method that delegates to the appropriate strategy
        
        Args:
            question: The user's question
            **kwargs: Additional parameters passed to the strategy method
            
        Returns:
            Dictionary with answer and metadata
        """
        if self.strategy == QueryStrategy.SIMPLE:
            return self._simple_query(question, **kwargs)
        elif self.strategy == QueryStrategy.ADVANCED:
            return self._advanced_query(question, **kwargs)
        else:  # OPTIMIZED
            return self._optimized_query(question, **kwargs)
    
    @classmethod
    def clear_cache(cls):
        """Clear the model and index cache"""
        cls._cache = {
            'llm': None,
            'embed_model': None,
            'index': None,
            'last_loaded': None,
            'settings': None
        }
        print("[INFO] Cache cleared")
    
    @classmethod
    def get_cache_status(cls) -> Dict[str, Any]:
        """Get current cache status"""
        return {
            "llm_loaded": cls._cache['llm'] is not None,
            "embed_model_loaded": cls._cache['embed_model'] is not None,
            "index_loaded": cls._cache['index'] is not None,
            "last_loaded": cls._cache['last_loaded'],
            "settings_loaded": cls._cache['settings'] is not None
        }

# Convenience functions for backward compatibility
def unified_ask(question: str, strategy: str = "optimized", **kwargs) -> Dict[str, Any]:
    """
    Convenience function for backward compatibility
    
    Args:
        question: The user's question
        strategy: Query strategy ('simple', 'advanced', 'optimized')
        **kwargs: Additional parameters
        
    Returns:
        Dictionary with answer and metadata
    """
    strategy_enum = QueryStrategy(strategy)
    engine = EmailQueryEngine(strategy=strategy_enum)
    return engine.query(question, **kwargs)

# Alias for the main optimized function
optimized_ask = lambda question, **kwargs: unified_ask(question, "optimized", **kwargs)
simple_ask = lambda question, **kwargs: unified_ask(question, "simple", **kwargs)
advanced_ask = lambda question, **kwargs: unified_ask(question, "advanced", **kwargs)

# Cache management functions
clear_cache = EmailQueryEngine.clear_cache
get_cache_status = EmailQueryEngine.get_cache_status