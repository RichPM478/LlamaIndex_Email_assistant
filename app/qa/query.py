# app/qa/lazy_query.py
"""
Ultra-fast lazy-loading query engine that defers all heavy imports until needed.
This should import in <50ms instead of 3500ms.
"""
from typing import Dict, Any, List, Optional, TYPE_CHECKING
import time
from enum import Enum
from app.qa.response_formatter import ResponseFormatter

# Type checking imports (no runtime cost)
if TYPE_CHECKING:
    from llama_index.core import VectorStoreIndex
    from app.config.settings import Settings

class QueryStrategy(Enum):
    """Query strategy options"""
    SIMPLE = "simple"
    ADVANCED = "advanced"  
    OPTIMIZED = "optimized"

class LazyEmailQueryEngine:
    """
    Ultra-fast lazy-loading query engine.
    Heavy imports are deferred until first actual query.
    """
    
    def __init__(self, strategy: QueryStrategy = QueryStrategy.OPTIMIZED, persist_dir: str = None, use_hybrid: bool = True):
        self.strategy = strategy
        
        # Resolve absolute path for index directory
        if persist_dir is None:
            from pathlib import Path
            # Get the project root (where data/ folder is located)
            current_file = Path(__file__).resolve()  # app/qa/query.py
            project_root = current_file.parent.parent.parent  # Go up 3 levels to project root
            self.persist_dir = str(project_root / "data" / "index")
        else:
            self.persist_dir = persist_dir
            
        self.use_hybrid = use_hybrid
        
        # Lazy-loaded components (None until needed)
        self._settings: Optional["Settings"] = None
        self._llm_configured = False
        self._embeddings_configured = False
        self._index: Optional["VectorStoreIndex"] = None
        self._hybrid_retriever = None
        self._last_loaded = None
        
        # Import states
        self._imports_loaded = False
    
    def _ensure_imports(self):
        """Lazy load all heavy imports only when needed"""
        if self._imports_loaded:
            return
        
        print("[LAZY] Loading imports on first use...")
        start = time.time()
        
        # Import heavy dependencies only now
        global StorageContext, load_index_from_storage, VectorStoreIndex
        global QueryBundle, get_response_synthesizer, VectorIndexRetriever  
        global MetadataFilters, MetadataFilter, FilterOperator, ResponseMode
        global configure_llm, configure_embeddings, get_settings
        
        from llama_index.core import StorageContext, load_index_from_storage, VectorStoreIndex, QueryBundle
        from llama_index.core.response_synthesizers import get_response_synthesizer, ResponseMode
        from llama_index.core.retrievers import VectorIndexRetriever
        from llama_index.core.vector_stores import MetadataFilters, MetadataFilter, FilterOperator
        
        from app.llm.provider import configure_llm
        from app.embeddings.provider import configure_embeddings  
        from app.config.settings import get_settings
        
        elapsed = time.time() - start
        print(f"[LAZY] Imports loaded in {elapsed*1000:.1f}ms")
        self._imports_loaded = True
    
    def _ensure_settings(self):
        """Lazy load settings"""
        if self._settings is None:
            self._ensure_imports()
            self._settings = get_settings()
        return self._settings
    
    def _ensure_models(self):
        """Lazy load and configure models"""
        if not self._llm_configured or not self._embeddings_configured:
            print("[LAZY] Configuring models on first use...")
            start = time.time()
            
            self._ensure_imports()
            settings = self._ensure_settings()
            
            if not self._llm_configured:
                configure_llm(settings)
                self._llm_configured = True
            
            if not self._embeddings_configured:
                configure_embeddings(settings)
                self._embeddings_configured = True
            
            elapsed = time.time() - start
            print(f"[LAZY] Models configured in {elapsed*1000:.1f}ms")
    
    def _ensure_index(self):
        """Lazy load vector index"""
        if self._index is None:
            print("[LAZY] Loading index on first use...")
            start = time.time()
            
            self._ensure_imports()
            
            # Check if index exists
            import os
            if not os.path.exists(self.persist_dir):
                print(f"[WARNING] Index directory not found: {self.persist_dir}")
                print("[INFO] Index needs to be built. Please run the indexing process first.")
                return None
            
            try:
                storage_context = StorageContext.from_defaults(persist_dir=self.persist_dir)
                self._index = load_index_from_storage(storage_context)
                self._last_loaded = time.time()
                
                elapsed = time.time() - start
                print(f"[LAZY] Index loaded in {elapsed*1000:.1f}ms")
            except Exception as e:
                print(f"[ERROR] Failed to load index: {e}")
                print("[INFO] Index may be corrupted or incompatible. Please rebuild the index.")
                return None
        
        return self._index
    
    def _sanitize_metadata_value(self, value):
        """Sanitize metadata values to prevent UI issues"""
        if not value:
            return "Unknown"
        
        import re  # Lazy import
        
        value = str(value).strip()
        value = re.sub(r'[<>"\'\&@#%\{\}\[\]\\]', '_', value)
        value = re.sub(r'\s+', ' ', value)
        
        if len(value) > 200:
            value = value[:197] + "..."
        
        return value if value else "Unknown"
    
    def _extract_sender_from_query(self, query: str) -> Optional[str]:
        """Extract sender name from queries"""
        if not isinstance(query, str) or not query.strip():
            return None
        
        import re  # Lazy import
        
        # Simple regex approach
        simple_match = re.search(r"from\s+([^,\.\?]+)", query.lower())
        if simple_match:
            return simple_match.group(1).strip()
        
        return None
    
    def _optimized_query(self, question: str, top_k: int = 5, **kwargs) -> Dict[str, Any]:
        """Optimized query with lazy loading"""
        total_start = time.time()
        
        # Lazy load everything
        self._ensure_models()
        index = self._ensure_index()
        
        # Handle case where index is not available
        if index is None:
            return {
                "answer": "Sorry, the email index is not available. Please build the index first by running the indexing process or using the 'Rebuild Index' button in the UI.",
                "confidence": 0.0,
                "citations": [],
                "query_time": time.time() - total_start,
                "metadata": {"error": "Index not available", "suggestion": "Run indexing process"}
            }
        
        # Check for sender filtering
        target_sender = self._extract_sender_from_query(question)
        actual_top_k = min(top_k * 2, 20) if target_sender else top_k
        
        # Create query engine with hybrid search if available
        if self.use_hybrid:
            try:
                # Lazy import hybrid retriever
                from app.retrieval.hybrid_retriever import create_hybrid_query_engine
                
                query_engine = create_hybrid_query_engine(
                    index=index,
                    vector_weight=0.6,
                    bm25_weight=0.4,
                    use_reranker=True,
                    response_mode=kwargs.get("response_mode", "compact")
                )
                print("[LAZY] Using hybrid search with reranking")
            except Exception as e:
                print(f"[WARNING] Could not initialize hybrid search: {e}")
                print("[WARNING] Falling back to standard vector search")
                query_engine = index.as_query_engine(
                    similarity_top_k=actual_top_k,
                    response_mode=kwargs.get("response_mode", "compact"),
                    streaming=kwargs.get("streaming", False),
                    verbose=False
                )
        else:
            query_engine = index.as_query_engine(
                similarity_top_k=actual_top_k,
                response_mode=kwargs.get("response_mode", "compact"),
                streaming=kwargs.get("streaming", False),
                verbose=False
            )
        
        # Execute query
        query_start = time.time()
        response = query_engine.query(question)
        query_time = time.time() - query_start
        
        # Get and filter source nodes
        source_nodes = getattr(response, 'source_nodes', [])
        
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
            meta = dict(node.node.metadata)
            text = node.node.text if hasattr(node.node, 'text') else ""
            
            # Clean up text content
            if "From:" in text and "Subject:" in text:
                lines = text.split('\n')
                content_start = 0
                for i, line in enumerate(lines):
                    if line.strip() == "":
                        content_start = i + 1
                        break
                text = '\n'.join(lines[content_start:])
            
            citation = {
                'from': self._sanitize_metadata_value(meta.get('from', 'Unknown')),
                'subject': self._sanitize_metadata_value(meta.get('subject', 'No subject')),
                'date': self._sanitize_metadata_value(meta.get('date', '')),
                'snippet': self._sanitize_metadata_value(text[:300].strip()),
                'score': node.score if hasattr(node, 'score') else None
            }
            citations.append(citation)
        
        total_time = time.time() - total_start
        
        # Format the response for better readability
        raw_answer = str(response)
        formatted_answer = ResponseFormatter.format_response(raw_answer, citations, question)
        
        # Add citations to formatted answer if requested
        if kwargs.get('include_sources', False):
            formatted_answer += ResponseFormatter.format_citations(citations)
        
        return {
            "answer": formatted_answer,
            "raw_answer": raw_answer,  # Keep raw for compatibility
            "citations": citations,
            "confidence": 0.8 if citations else 0.5,  # Simple confidence based on citations
            "metadata": {
                "total_time": total_time,
                "query_time": query_time,
                "top_k": top_k,
                "filtered_by_sender": target_sender is not None,
                "lazy_loaded": True,
                "strategy": "lazy_optimized",
                "hybrid_search": self.use_hybrid
            }
        }
    
    def query(self, question: str, **kwargs) -> Dict[str, Any]:
        """Main query method - always uses optimized approach with lazy loading"""
        return self._optimized_query(question, **kwargs)
    
    @classmethod
    def clear_cache(cls):
        """Clear any caches (for compatibility)"""
        print("[LAZY] Cache cleared")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get current lazy loading status (compatible with unified engine)"""
        return {
            # Unified engine compatibility
            "llm_loaded": self._llm_configured,
            "embed_model_loaded": self._embeddings_configured,
            "index_loaded": self._index is not None,
            "last_loaded": self._last_loaded,
            "settings_loaded": self._settings is not None,
            # Lazy engine specific
            "imports_loaded": self._imports_loaded,
            "llm_configured": self._llm_configured,
            "embeddings_configured": self._embeddings_configured,
        }

# Create global instance for singleton behavior
_global_engine: Optional[LazyEmailQueryEngine] = None

def get_engine(strategy: str = "optimized") -> LazyEmailQueryEngine:
    """Get or create the global lazy engine instance"""
    global _global_engine
    if _global_engine is None:
        _global_engine = LazyEmailQueryEngine(strategy=QueryStrategy.OPTIMIZED)
    return _global_engine

# Main query function
def ask(question: str, **kwargs) -> Dict[str, Any]:
    """Process a question and return formatted answer with citations"""
    engine = get_engine("optimized")
    return engine.query(question, **kwargs)

# Backward compatibility alias (to be removed later)
lazy_optimized_ask = ask

def get_cache_status() -> Dict[str, Any]:
    """Get cache status from global engine"""
    engine = get_engine()
    return engine.get_cache_status()

def clear_cache():
    """Clear cache from global engine"""
    global _global_engine
    _global_engine = None
    print("[LAZY] Global engine cleared")

# Aliases for drop-in replacement
optimized_ask = lazy_optimized_ask
simple_ask = lazy_optimized_ask  # All strategies use optimized under the hood
advanced_ask = lazy_optimized_ask