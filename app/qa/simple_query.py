# app/qa/simple_query.py
"""
Simpler query approach that works around metadata filtering issues
"""
from typing import Dict, Any, List
from llama_index.core import StorageContext, load_index_from_storage
from app.config.settings import get_settings
from app.llm.provider import configure_llm
from app.embeddings.provider import configure_embeddings
import re


def simple_ask(question: str, top_k: int = 10) -> Dict[str, Any]:
    """
    Simpler query that uses semantic search and post-filters results
    """
    # Configure LLM + embeddings
    s = get_settings()
    configure_llm(s)
    configure_embeddings(s)
    
    # Load index
    storage_context = StorageContext.from_defaults(persist_dir="data/index")
    index = load_index_from_storage(storage_context)
    
    # Check if user is looking for specific sender
    sender_match = re.search(r"from\s+([^,\.\?]+)", question.lower())
    target_sender = sender_match.group(1).strip() if sender_match else None
    
    # Create query engine with more results than needed (we'll filter later)
    query_engine = index.as_query_engine(
        similarity_top_k=top_k * 3 if target_sender else top_k,
        response_mode="compact"
    )
    
    # Execute query
    response = query_engine.query(question)
    
    # Get source nodes
    source_nodes = getattr(response, 'source_nodes', [])
    
    # Post-filter if looking for specific sender
    if target_sender:
        print(f"[DEBUG] Filtering for sender: {target_sender}")
        filtered_nodes = []
        for node in source_nodes:
            from_field = node.node.metadata.get('from', '').lower()
            from_normalized = node.node.metadata.get('from_normalized', '').lower()
            
            if target_sender in from_field or target_sender in from_normalized:
                filtered_nodes.append(node)
        
        print(f"[DEBUG] Filtered from {len(source_nodes)} to {len(filtered_nodes)} results")
        
        # Use filtered nodes if any found
        if filtered_nodes:
            source_nodes = filtered_nodes[:top_k]
        else:
            print(f"[DEBUG] No emails from {target_sender} found, showing semantic matches")
    
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
        "metadata_filters_applied": target_sender is not None
    }