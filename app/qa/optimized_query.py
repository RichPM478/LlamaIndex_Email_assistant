# app/qa/optimized_query.py
"""
Optimized query engine with model caching and performance improvements
"""
from typing import Dict, Any, List, Optional
from llama_index.core import StorageContext, load_index_from_storage, VectorStoreIndex
from app.config.settings import get_settings
from app.llm.provider import configure_llm
from app.embeddings.provider import configure_embeddings
import re
import time

# Global cache for models and index
_cache = {
    'llm': None,
    'embed_model': None,
    'index': None,
    'last_loaded': None
}

def _ensure_models_loaded():
    """Ensure models are loaded and cached"""
    if _cache['llm'] is None or _cache['embed_model'] is None:
        print("[INFO] Loading models into cache...")
        s = get_settings()
        _cache['llm'] = configure_llm(s)
        _cache['embed_model'] = configure_embeddings(s)
        print("[INFO] Models cached successfully")
    return _cache['llm'], _cache['embed_model']

def _ensure_index_loaded() -> VectorStoreIndex:
    """Ensure index is loaded and cached"""
    if _cache['index'] is None:
        print("[INFO] Loading index into cache...")
        storage_context = StorageContext.from_defaults(persist_dir="data/index")
        _cache['index'] = load_index_from_storage(storage_context)
        _cache['last_loaded'] = time.time()
        print("[INFO] Index cached successfully")
    return _cache['index']

def clear_cache():
    """Clear the cache (useful for reloading after index updates)"""
    global _cache
    _cache = {
        'llm': None,
        'embed_model': None,
        'index': None,
        'last_loaded': None
    }
    print("[INFO] Cache cleared")

def optimized_ask(
    question: str, 
    top_k: int = 5,
    response_mode: str = "compact",
    streaming: bool = False
) -> Dict[str, Any]:
    """
    Optimized query with caching and performance improvements
    
    Args:
        question: The user's question
        top_k: Number of results to retrieve (reduced default for speed)
        response_mode: Response synthesis mode
        streaming: Whether to stream the response
    
    Returns:
        Dictionary with answer and metadata
    """
    start_time = time.time()
    
    # Ensure models and index are loaded
    _ensure_models_loaded()
    index = _ensure_index_loaded()
    
    # Check for sender-specific queries
    sender_match = re.search(r"from\s+([^,\.\?]+)", question.lower())
    target_sender = sender_match.group(1).strip() if sender_match else None
    
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
            "cache_used": True
        }
    }

def get_cache_status() -> Dict[str, Any]:
    """Get current cache status"""
    return {
        "llm_loaded": _cache['llm'] is not None,
        "embed_model_loaded": _cache['embed_model'] is not None,
        "index_loaded": _cache['index'] is not None,
        "last_loaded": _cache['last_loaded']
    }