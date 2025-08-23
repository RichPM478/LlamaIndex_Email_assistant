"""
Bridge to connect old query interface with new flexible system
This allows the original UI to work with the new flexible architecture
"""
import sys
from pathlib import Path
from typing import Dict, Any

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Global flexible engine instance
_flexible_engine = None

def get_flexible_engine():
    """Get or create flexible engine instance"""
    global _flexible_engine
    if _flexible_engine is None:
        from app.core.flexible_query_engine import FlexibleQueryEngine
        _flexible_engine = FlexibleQueryEngine()
        
        # Load the best working experiment
        success = _flexible_engine.load_experiment("mixedbread_hybrid")
        if not success:
            print("[WARNING] Failed to load mixedbread_hybrid experiment")
    
    return _flexible_engine

def ask(query: str, top_k: int = 10, **kwargs) -> Dict[str, Any]:
    """
    Bridge function that mimics the old ask() interface
    but uses the new flexible system
    """
    try:
        engine = get_flexible_engine()
        result = engine.query(query, top_k=top_k)
        
        if 'error' in result:
            # Return old-style error response
            return {
                'answer': f"Sorry, I encountered an error: {result['error']}",
                'confidence': 0.0,
                'citations': [],
                'metadata': {'error': result['error']}
            }
        
        # Convert to old-style response format
        citations = []
        for doc in result['results']:
            citation = {
                'from': doc.get('from', '(Unknown Sender)'),
                'subject': doc.get('subject', 'No Subject'),
                'date': doc.get('date', 'Unknown Date'),
                'snippet': doc['content'][:120] + "..." if len(doc['content']) > 120 else doc['content'],
                'score': doc['score']
            }
            citations.append(citation)
        
        # Generate answer from top results
        if citations:
            answer = f"Found {len(citations)} relevant emails:\\n\\n"
            for i, citation in enumerate(citations[:3], 1):
                answer += f"{i}. **{citation['subject']}** (from {citation['from']})\\n"
                answer += f"   {citation['snippet']}\\n\\n"
        else:
            answer = "I couldn't find any relevant emails for your query."
        
        # Calculate simple confidence based on top score
        confidence = 0.8 if citations and citations[0]['score'] > 0.5 else 0.5 if citations else 0.0
        
        return {
            'answer': answer,
            'confidence': confidence,
            'citations': citations,
            'metadata': {
                'total_time': result['timing']['total'],
                'query_time': result['timing']['retrieval'],
                'top_k': len(result['results']),
                'experiment': result['experiment'],
                'flexible_system': True
            }
        }
        
    except Exception as e:
        print(f"[ERROR] Flexible query bridge failed: {e}")
        return {
            'answer': f"Sorry, the search system is currently unavailable. Error: {str(e)}",
            'confidence': 0.0,
            'citations': [],
            'metadata': {'error': str(e)}
        }

def get_cache_status() -> Dict[str, Any]:
    """
    Bridge function for cache status
    """
    try:
        engine = get_flexible_engine()
        current_config = engine.get_current_config()
        
        return {
            'llm_loaded': True,
            'embed_model_loaded': current_config is not None,
            'index_loaded': engine._vectors_loaded,
            'imports_loaded': True,
            'llm_configured': True,
            'embeddings_configured': current_config is not None,
            'flexible_system': True,
            'current_experiment': current_config.name if current_config else None
        }
    except Exception as e:
        return {
            'llm_loaded': False,
            'embed_model_loaded': False,
            'index_loaded': False,
            'imports_loaded': False,
            'llm_configured': False,
            'embeddings_configured': False,
            'error': str(e)
        }