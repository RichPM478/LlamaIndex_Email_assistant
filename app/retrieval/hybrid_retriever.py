# app/retrieval/hybrid_retriever.py
"""
Hybrid retrieval system combining vector search and BM25 keyword search
with cross-encoder reranking for superior retrieval quality
"""

from typing import List, Dict, Any, Optional
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.base_retriever import BaseRetriever
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.node_parser import SentenceSplitter
import torch
from sentence_transformers import CrossEncoder


class HybridRetriever(BaseRetriever):
    """
    Advanced hybrid retriever combining:
    1. Dense vector search (semantic similarity)
    2. BM25 sparse retrieval (keyword matching)
    3. Cross-encoder reranking (precision improvement)
    """
    
    def __init__(
        self,
        index: VectorStoreIndex,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4,
        rerank_top_k: int = 10,
        use_reranker: bool = True,
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ):
        """
        Initialize hybrid retriever
        
        Args:
            index: Vector store index
            vector_weight: Weight for vector search results (0-1)
            bm25_weight: Weight for BM25 results (0-1)
            rerank_top_k: Number of results to rerank
            use_reranker: Whether to use cross-encoder reranking
            reranker_model: Cross-encoder model for reranking
        """
        # Initialize base retriever
        super().__init__()
        
        self.index = index
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.rerank_top_k = rerank_top_k
        self.use_reranker = use_reranker
        
        # Initialize retrievers
        self.vector_retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=rerank_top_k * 2  # Get more candidates for reranking
        )
        
        # BM25 retriever for keyword search
        self.bm25_retriever = BM25Retriever.from_defaults(
            nodes=list(index.docstore.docs.values()),
            similarity_top_k=rerank_top_k * 2
        )
        
        # Initialize cross-encoder for reranking if enabled
        self.cross_encoder = None
        if use_reranker:
            try:
                device = "cuda" if torch.cuda.is_available() else "cpu"
                self.cross_encoder = CrossEncoder(
                    reranker_model,
                    max_length=512,
                    device=device
                )
                print(f"[HYBRID] Initialized cross-encoder reranker on {device.upper()}")
            except Exception as e:
                print(f"[WARNING] Could not initialize cross-encoder: {e}")
                print("[WARNING] Falling back to hybrid search without reranking")
                self.use_reranker = False
    
    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """
        Internal retrieve method required by BaseRetriever
        
        Args:
            query_bundle: Query bundle from query engine
            
        Returns:
            List of nodes with scores
        """
        # Handle both string and QueryBundle inputs
        if isinstance(query_bundle, str):
            query_bundle = QueryBundle(query_str=query_bundle)
        
        query = query_bundle.query_str
        
        # Get results from both retrievers
        vector_results = self.vector_retriever.retrieve(query_bundle)
        bm25_results = self.bm25_retriever.retrieve(query_bundle)
        
        # Combine and deduplicate results
        combined_results = self._combine_results(vector_results, bm25_results)
        
        # Rerank if enabled
        if self.use_reranker and self.cross_encoder:
            combined_results = self._rerank_results(query, combined_results)
        
        # Return top k results (default to 5 if not specified)
        top_k = getattr(self, '_similarity_top_k', 5)
        return combined_results[:top_k]
    
    def _combine_results(
        self,
        vector_results: List[NodeWithScore],
        bm25_results: List[NodeWithScore]
    ) -> List[NodeWithScore]:
        """
        Combine results from vector and BM25 search with weighted scoring
        """
        # Create score dictionaries
        vector_scores = {
            node.node.id_: node.score * self.vector_weight
            for node in vector_results
        }
        
        bm25_scores = {
            node.node.id_: node.score * self.bm25_weight
            for node in bm25_results
        }
        
        # Combine scores
        all_node_ids = set(vector_scores.keys()) | set(bm25_scores.keys())
        combined_nodes = {}
        
        for node_id in all_node_ids:
            # Get the node (from either result set)
            node = None
            for n in vector_results:
                if n.node.id_ == node_id:
                    node = n.node
                    break
            if not node:
                for n in bm25_results:
                    if n.node.id_ == node_id:
                        node = n.node
                        break
            
            if node:
                # Calculate combined score
                combined_score = vector_scores.get(node_id, 0) + bm25_scores.get(node_id, 0)
                combined_nodes[node_id] = NodeWithScore(node=node, score=combined_score)
        
        # Sort by combined score
        sorted_results = sorted(
            combined_nodes.values(),
            key=lambda x: x.score,
            reverse=True
        )
        
        return sorted_results
    
    def _rerank_results(
        self,
        query: str,
        results: List[NodeWithScore]
    ) -> List[NodeWithScore]:
        """
        Rerank results using cross-encoder
        """
        if not results:
            return results
        
        # Prepare pairs for cross-encoder
        pairs = []
        for node_with_score in results[:self.rerank_top_k]:
            text = node_with_score.node.get_content()
            
            # Add metadata context for better reranking
            metadata = node_with_score.node.metadata
            context = f"From: {metadata.get('from', 'Unknown')}\n"
            context += f"Subject: {metadata.get('subject', 'No Subject')}\n\n"
            context += text
            
            pairs.append([query, context])
        
        # Get cross-encoder scores
        try:
            ce_scores = self.cross_encoder.predict(pairs)
            
            # Update scores with cross-encoder results
            for i, score in enumerate(ce_scores):
                if i < len(results):
                    # Combine original score with reranker score
                    original_score = results[i].score
                    # Weight: 70% reranker, 30% original
                    results[i].score = 0.7 * float(score) + 0.3 * original_score
            
            # Re-sort by new scores
            results = sorted(results, key=lambda x: x.score, reverse=True)
            
        except Exception as e:
            print(f"[WARNING] Reranking failed: {e}")
        
        return results
    
    def get_retriever_info(self) -> Dict[str, Any]:
        """Get information about the retriever configuration"""
        return {
            "type": "hybrid",
            "vector_weight": self.vector_weight,
            "bm25_weight": self.bm25_weight,
            "reranking_enabled": self.use_reranker,
            "reranker_model": self.cross_encoder.model_name if self.cross_encoder else None,
            "device": "cuda" if torch.cuda.is_available() else "cpu"
        }


def create_hybrid_query_engine(
    index: VectorStoreIndex,
    vector_weight: float = 0.6,
    bm25_weight: float = 0.4,
    use_reranker: bool = True,
    response_mode: str = "tree_summarize"
):
    """
    Create a query engine with hybrid retrieval
    
    Args:
        index: Vector store index
        vector_weight: Weight for vector search
        bm25_weight: Weight for BM25 search
        use_reranker: Whether to use cross-encoder reranking
        response_mode: Response synthesis mode
        
    Returns:
        Query engine with hybrid retrieval
    """
    from llama_index.core.query_engine import RetrieverQueryEngine
    from llama_index.core.response_synthesizers import get_response_synthesizer
    
    # Create hybrid retriever
    hybrid_retriever = HybridRetriever(
        index=index,
        vector_weight=vector_weight,
        bm25_weight=bm25_weight,
        use_reranker=use_reranker
    )
    
    # Create response synthesizer
    response_synthesizer = get_response_synthesizer(
        response_mode=response_mode
    )
    
    # Create query engine with custom retriever
    # Note: We need to implement the BaseRetriever interface properly
    query_engine = RetrieverQueryEngine(
        retriever=hybrid_retriever,
        response_synthesizer=response_synthesizer
    )
    
    return query_engine