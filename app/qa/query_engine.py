# app/qa/query_engine.py
from typing import Dict, Any, Optional, List
from llama_index.core import StorageContext, load_index_from_storage, QueryBundle
from llama_index.core.response_synthesizers import get_response_synthesizer, ResponseMode
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter, FilterOperator
from llama_index.core.schema import NodeWithScore
import re

from app.config.settings import get_settings
from app.llm.provider import configure_llm
from app.embeddings.provider import configure_embeddings


def load_index(persist_dir: str = "data/index"):
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    return load_index_from_storage(storage_context)


def extract_sender_from_query(query: str) -> Optional[str]:
    """Extract sender name from queries like 'emails from X' or 'from X'"""
    patterns = [
        r"(?:emails?\s+)?from\s+([^,\.\?]+)",
        r"sent\s+by\s+([^,\.\?]+)",
        r"([^,\.\?]+?)\s+emails?",
    ]
    
    query_lower = query.lower()
    for pattern in patterns:
        match = re.search(pattern, query_lower, re.IGNORECASE)
        if match:
            sender = match.group(1).strip()
            # Clean up common words
            sender = sender.replace("emails", "").replace("email", "").strip()
            return sender
    return None


def ask(question: str, top_k: int = 6) -> Dict[str, Any]:
    """
    Enhanced query function with better error handling for metadata filtering
    """
    # Configure LLM + embeddings
    s = get_settings()
    configure_llm(s)
    configure_embeddings(s)

    index = load_index()
    
    # Check if this is a metadata-specific query
    sender = extract_sender_from_query(question)
    
    # Try different retrieval strategies
    nodes = []
    metadata_filters_applied = False
    
    try:
        if sender:
            # Try with metadata filtering first
            print(f"[DEBUG] Looking for emails from: {sender}")
            
            # Try exact match first
            filters = MetadataFilters(
                filters=[
                    MetadataFilter(
                        key="from_normalized",  # Use normalized field if available
                        value=sender.lower(),
                        operator=FilterOperator.CONTAINS
                    )
                ]
            )
            
            try:
                retriever = VectorIndexRetriever(
                    index=index,
                    similarity_top_k=top_k * 2,
                    filters=filters
                )
                nodes = retriever.retrieve(QueryBundle(query_str=question))
                metadata_filters_applied = True
                print(f"[DEBUG] Found {len(nodes)} results with normalized filter")
            except Exception as e:
                print(f"[DEBUG] Normalized filter failed: {e}")
                
            # If no results, try with regular from field
            if len(nodes) == 0:
                filters = MetadataFilters(
                    filters=[
                        MetadataFilter(
                            key="from",
                            value=sender,
                            operator=FilterOperator.CONTAINS
                        )
                    ]
                )
                
                try:
                    retriever = VectorIndexRetriever(
                        index=index,
                        similarity_top_k=top_k * 2,
                        filters=filters
                    )
                    nodes = retriever.retrieve(QueryBundle(query_str=question))
                    metadata_filters_applied = True
                    print(f"[DEBUG] Found {len(nodes)} results with 'from' filter")
                except Exception as e:
                    print(f"[DEBUG] 'from' filter failed: {e}")
    
    except Exception as e:
        print(f"[DEBUG] Metadata filtering error: {e}")
        print("[DEBUG] Falling back to semantic search")
    
    # If metadata filtering failed or returned no results, use semantic search
    if len(nodes) == 0:
        print("[DEBUG] Using semantic search without filters")
        try:
            retriever = VectorIndexRetriever(
                index=index,
                similarity_top_k=top_k
            )
            nodes = retriever.retrieve(QueryBundle(query_str=question))
        except Exception as e:
            print(f"[ERROR] Retrieval failed: {e}")
            # Return empty result if all retrieval methods fail
            return {
                "answer": "I encountered an error while searching. Please try rephrasing your query.",
                "confidence": None,
                "citations": [],
                "metadata_filters_applied": False,
                "error": str(e)
            }
    
    # If we still have no nodes, return a helpful message
    if len(nodes) == 0:
        return {
            "answer": f"I couldn't find any emails matching your query. {'I specifically looked for emails from ' + sender + ' but found none.' if sender else 'Try rephrasing your search.'}",
            "confidence": None,
            "citations": [],
            "metadata_filters_applied": metadata_filters_applied
        }
    
    # Build enhanced prompt with explicit instructions
    context_str = "\n\n---\n\n".join([
        f"Email from: {n.node.metadata.get('from', 'Unknown')}\n"
        f"Subject: {n.node.metadata.get('subject', 'No subject')}\n"
        f"Date: {n.node.metadata.get('date', 'Unknown date')}\n"
        f"Content: {n.node.text[:500]}"
        for n in nodes[:top_k]
    ])
    
    # Create a more explicit prompt
    enhanced_prompt = f"""Based on the following email excerpts, answer this question: {question}

IMPORTANT: Only use information explicitly stated in the email excerpts below. If the information is not present, say so clearly.

Email Excerpts:
{context_str}

Answer:"""
    
    # Get response from LLM
    from llama_index.core.llms import ChatMessage, MessageRole
    from llama_index.core import Settings
    
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content="You are a helpful assistant that answers questions about emails. Only use information explicitly provided in the context. Do not make assumptions or add information not present in the source material."),
        ChatMessage(role=MessageRole.USER, content=enhanced_prompt)
    ]
    
    try:
        response = Settings.llm.chat(messages)
        answer = str(response.message.content)
    except Exception as e:
        print(f"[ERROR] LLM response failed: {e}")
        answer = "I found relevant emails but encountered an error generating a response."
    
    # Prepare citations
    citations = []
    for sn in nodes[:top_k]:
        try:
            citation = dict(sn.node.metadata) if hasattr(sn.node, 'metadata') else {}
            citation['score'] = sn.score if hasattr(sn, 'score') else None
            citation['snippet'] = sn.node.text[:200] if hasattr(sn.node, 'text') else ""
            citations.append(citation)
        except Exception as e:
            print(f"[WARNING] Citation extraction error: {e}")
            continue

    return {
        "answer": answer,
        "confidence": nodes[0].score if nodes and hasattr(nodes[0], 'score') else None,
        "citations": citations,
        "metadata_filters_applied": metadata_filters_applied
    }