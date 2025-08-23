"""
Flexible Indexing System
Builds model-agnostic indexes that can be used with different embedding models
"""
import json
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from tqdm import tqdm

from .flexible_architecture import (
    FlexibleVectorStore, FlexibleEmbeddingEngine, ModelConfig,
    EmbeddingProvider, PREDEFINED_EXPERIMENTS
)

logger = logging.getLogger(__name__)

class FlexibleIndexer:
    """
    Indexer that creates model-agnostic vector stores
    """
    
    def __init__(self):
        self.embedding_engine = FlexibleEmbeddingEngine()
    
    def build_index(self, 
                   email_documents: List[Dict], 
                   config_name: str,
                   output_path: str = "data/flexible_index",
                   batch_size: int = 64) -> bool:
        """
        Build flexible index from email documents
        
        Args:
            email_documents: List of processed email documents
            config_name: Name of embedding configuration to use
            output_path: Where to save the index
            batch_size: Batch size for embedding generation
        """
        
        # Get embedding configuration
        if config_name in PREDEFINED_EXPERIMENTS:
            embedding_config = PREDEFINED_EXPERIMENTS[config_name].embedding_model
        else:
            logger.error(f"Unknown configuration: {config_name}")
            return False
        
        # Load embedding model
        try:
            self.embedding_engine.load_model(embedding_config)
            logger.info(f"Loaded embedding model: {embedding_config.model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            return False
        
        # Prepare documents and texts
        texts = []
        documents = []
        from datetime import datetime
        metadata = {
            'total_documents': len(email_documents),
            'embedding_config': config_name,
            'dimensions': embedding_config.dimensions,
            'created_at': str(datetime.now())
        }
        
        logger.info(f"Preparing {len(email_documents)} documents for indexing...")
        
        for i, email_doc in enumerate(email_documents):
            # Extract text content for embedding
            text_content = self._extract_text_content(email_doc)
            texts.append(text_content)
            
            # Store full document with metadata
            doc_with_metadata = {
                'content': text_content,
                'metadata': email_doc.get('metadata', {}),
                'document_id': i,
                'original_email': email_doc  # Keep original for reference
            }
            documents.append(doc_with_metadata)
        
        # Generate embeddings in batches
        logger.info(f"Generating embeddings with {embedding_config.model_name}...")
        all_vectors = []
        
        for i in tqdm(range(0, len(texts), batch_size), desc="Embedding batches"):
            batch_texts = texts[i:i + batch_size]
            batch_vectors = self.embedding_engine.encode(batch_texts)
            all_vectors.append(batch_vectors)
        
        # Combine all vectors
        vectors = np.vstack(all_vectors)
        logger.info(f"Generated {len(vectors)} embeddings of dimension {vectors.shape[1]}")
        
        # Build BM25 index for hybrid search
        bm25_index = self._build_bm25_index(texts)
        
        # Save to flexible vector store
        vector_store = FlexibleVectorStore(Path(output_path))
        vector_store.save_vectors(vectors, metadata, documents, embedding_config)
        
        # Save BM25 index separately
        if bm25_index:
            with open(vector_store.bm25_file, 'wb') as f:
                pickle.dump(bm25_index, f)
            logger.info("BM25 index saved")
        
        logger.info(f"Flexible index built successfully at {output_path}")
        return True
    
    def _extract_text_content(self, email_doc: Dict) -> str:
        """Extract text content for embedding from email document"""
        
        # Try different content fields
        content_fields = ['clean_body', 'body', 'content', 'text']
        main_content = ""
        
        for field in content_fields:
            if field in email_doc and email_doc[field]:
                main_content = str(email_doc[field])
                break
        
        # Add metadata context
        metadata = email_doc.get('metadata', {})
        
        # Build enhanced content for better embedding
        enhanced_content = []
        
        # Add subject
        if 'subject' in metadata or 'clean_subject' in email_doc:
            subject = metadata.get('subject') or email_doc.get('clean_subject', '')
            if subject:
                enhanced_content.append(f"Subject: {subject}")
        
        # Add sender
        if 'from' in metadata or 'clean_sender' in email_doc:
            sender = metadata.get('from') or email_doc.get('clean_sender', '')
            if sender:
                enhanced_content.append(f"From: {sender}")
        
        # Add main content
        if main_content:
            enhanced_content.append(main_content)
        
        # Add attachment content if available
        if 'attachments' in email_doc:
            for attachment in email_doc.get('attachments', []):
                if attachment.get('extracted_content', {}).get('text'):
                    att_content = attachment['extracted_content']['text'][:1000]  # Limit attachment text
                    enhanced_content.append(f"Attachment: {att_content}")
        
        return "\\n".join(enhanced_content)
    
    def _build_bm25_index(self, texts: List[str]) -> Optional[Any]:
        """Build BM25 index for keyword search"""
        try:
            from rank_bm25 import BM25Okapi
            
            # Simple tokenization (can be improved)
            tokenized_texts = [text.lower().split() for text in texts]
            bm25 = BM25Okapi(tokenized_texts)
            
            logger.info("BM25 index built successfully")
            return bm25
            
        except ImportError:
            logger.warning("rank_bm25 not installed - BM25 search will be unavailable")
            return None
        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
            return None

def build_index_from_emails(raw_email_file: str, 
                          config_name: str = "mixedbread_hybrid",
                          output_path: str = "data/flexible_index") -> bool:
    """
    Convenience function to build index from raw email file
    """
    from datetime import datetime
    from tqdm import tqdm
    
    # Load raw emails
    with open(raw_email_file, 'r', encoding='utf-8') as f:
        raw_emails = json.load(f)
    
    logger.info(f"Loaded {len(raw_emails)} raw emails from {raw_email_file}")
    
    # Process emails using existing parser
    from app.ingest.mailparser_adapter import MailParserAdapter
    parser = MailParserAdapter()
    
    processed_emails = []
    for raw_email in tqdm(raw_emails, desc="Processing emails"):
        try:
            parsed = parser.parse_email_advanced(raw_email)
            
            # Skip very low quality emails
            if parsed['quality_score'] < 30 or len(parsed['clean_body'].strip()) < 10:
                continue
            
            # Format for flexible indexer
            email_doc = {
                'clean_body': parsed['clean_body'],
                'metadata': {
                    'subject': parsed['clean_subject'],
                    'from': parsed['clean_sender'],
                    'date': raw_email.get('date'),
                    'quality_score': parsed['quality_score'],
                    'message_id': raw_email.get('message_id'),
                    'folder': raw_email.get('folder', 'INBOX')
                },
                'attachments': parsed.get('attachments', [])
            }
            processed_emails.append(email_doc)
            
        except Exception as e:
            logger.warning(f"Failed to process email: {e}")
            continue
    
    logger.info(f"Successfully processed {len(processed_emails)} emails")
    
    # Build index
    indexer = FlexibleIndexer()
    return indexer.build_index(processed_emails, config_name, output_path)

if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.core.flexible_indexer <raw_email_file> [config_name] [output_path]")
        sys.exit(1)
    
    raw_file = sys.argv[1]
    config = sys.argv[2] if len(sys.argv) > 2 else "mixedbread_hybrid"
    output = sys.argv[3] if len(sys.argv) > 3 else "data/flexible_index"
    
    success = build_index_from_emails(raw_file, config, output)
    if success:
        print(f"Index built successfully at {output}")
    else:
        print("Index build failed")
        sys.exit(1)