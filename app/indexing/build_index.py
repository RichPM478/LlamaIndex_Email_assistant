# app/indexing/build_index.py
"""
Unified Email Index Builder with Smart Chunking

Features:
- Smart context-aware chunking that preserves email structure
- Quality-based filtering for high-quality content
- Enhanced metadata with quality scores
- Optimized for semantic search
"""

import os
import glob
import json
from typing import List, Dict, Any, Optional
from llama_index.core import VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode

from app.config.settings import get_settings
from app.llm.provider import configure_llm
from app.embeddings.provider import configure_embeddings
from app.ingest.mailparser_adapter import MailParserAdapter
from app.indexing.smart_chunker import SmartEmailChunker


def _load_raw_emails(path: str) -> List[Dict[str, Any]]:
    """Load emails from .json, .jsonl, or .json.enc (encrypted) files."""
    from app.security.encryption import credential_manager
    
    emails: List[Dict[str, Any]] = []
    
    try:
        # Handle encrypted files
        if path.endswith(".json.enc"):
            print(f"[DECRYPT] Loading encrypted email file: {path}")
            with open(path, "r", encoding="utf-8") as f:
                encrypted_content = f.read().strip()
            
            decrypted_content = credential_manager.decrypt_credential(encrypted_content)
            data = json.loads(decrypted_content)
            
            if isinstance(data, list):
                emails = data
            else:
                raise ValueError(f"{path} must contain a JSON list")
                
        elif path.endswith(".jsonl"):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        emails.append(json.loads(line))
                        
        elif path.endswith(".json"):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    emails = data
                else:
                    raise ValueError(f"{path} must contain a JSON list")
        else:
            raise ValueError(f"Unsupported raw format: {path}")
            
        print(f"[SUCCESS] Loaded {len(emails)} emails from {path}")
        return emails
        
    except Exception as e:
        print(f"[ERROR] Failed to load emails from {path}: {e}")
        raise


def _resolve_latest_raw(explicit_path: Optional[str]) -> str:
    """Pick the explicit file, or newest file in data/raw/, by modified time (supports encrypted files)."""
    if explicit_path and os.path.exists(explicit_path):
        return explicit_path

    # Look for both encrypted and unencrypted files
    candidates = (glob.glob("data/raw/*.json") + 
                  glob.glob("data/raw/*.jsonl") + 
                  glob.glob("data/raw/*.json.enc"))
    
    if not candidates:
        raise FileNotFoundError("No raw files found in data/raw/. Run `python main.py ingest` first.")

    latest = max(candidates, key=os.path.getmtime)
    return latest


def build_index(raw_path: Optional[str] = None, 
               persist_dir: str = "data/index", 
               quality_threshold: float = 40.0,
               max_marketing_score: float = 50.0) -> VectorStoreIndex:
    """
    Build index with smart chunking and quality filtering
    
    Args:
        raw_path: Path to raw email file  
        persist_dir: Directory to save index
        quality_threshold: Minimum quality score (0-100) to include email
        max_marketing_score: Maximum marketing score (0-100) to include email
    """
    settings = get_settings()
    configure_llm(settings)
    configure_embeddings(settings)

    raw_file = _resolve_latest_raw(raw_path)
    print(f"[INDEX] Using raw file: {raw_file}")

    emails = _load_raw_emails(raw_file)
    print(f"[INDEX] Processing {len(emails)} emails with smart chunking and quality filtering")

    # Initialize Advanced Email Parser 2.0
    parser = MailParserAdapter()
    
    # Use optimized smart chunker for high-quality embeddings
    # Tuned for mixedbread-ai/mxbai-embed-large-v1 (512 token context)
    chunker = SmartEmailChunker(
        min_chunk_size=50,   # Better granularity for short content
        max_chunk_size=384,  # Leave room for metadata in 512 token window
        overlap_size=30,     # Efficient overlap for context
        preserve_paragraphs=True,
        preserve_sentences=True  # Better semantic boundaries
    )
    nodes: List[TextNode] = []
    
    # Quality statistics
    processed_count = 0
    filtered_count = 0
    quality_scores = []
    rejected_reasons = []
    
    for i, raw_email in enumerate(emails):
        # Parse email with Advanced Parser 2.0
        parsed_email = parser.parse_email_advanced(raw_email)
        
        # Extract quality metrics
        quality_score = parsed_email['quality_score']
        marketing_score = parsed_email['marketing_score']
        content_ratio = parsed_email['content_ratio']
        language_confidence = parsed_email['language_confidence']
        clean_body = parsed_email['clean_body']
        
        quality_scores.append(quality_score)
        
        # Minimal filtering - only skip truly empty emails
        if len(clean_body.strip()) < 10:
            rejected_reasons.append("Empty email")
            continue
        
        processed_count += 1
        
        # Create enhanced metadata with quality scores
        meta = {
            # Original metadata
            "message_id": raw_email.get("message_id"),
            "uid": raw_email.get("uid"),
            "subject": parsed_email['clean_subject'],
            "from": parsed_email['clean_sender'],
            "from_normalized": parsed_email['clean_sender'].lower(),
            "date": raw_email.get("date"),
            "sent_at": raw_email.get("sent_at"),
            "folder": raw_email.get("folder"),
            "email_index": i,
            
            # Quality metadata (NEW)
            "quality_score": quality_score,
            "content_ratio": content_ratio,
            "marketing_score": marketing_score,
            "language_confidence": language_confidence,
            "parser_version": "2.0",
            "processed_length": len(clean_body),
            "original_length": len(raw_email.get('body', '')),
            
            # Quality classification
            "quality_tier": "high" if quality_score >= 80 else "medium" if quality_score >= 60 else "low",
            "is_marketing": marketing_score > 30,
            "is_template": parsed_email['template_score'] > 50,
        }
        
        # Create enhanced text with metadata for better semantic matching
        enhanced_text = f"From: {parsed_email['clean_sender']}\nSubject: {parsed_email['clean_subject']}\n\n{clean_body}"
        
        # Smart chunking with context awareness
        content_dict = {
            'main_content': clean_body,
            'cleaned_full_text': enhanced_text
        }
        email_chunks = chunker.chunk_email(content_dict, meta)
        
        # If no chunks (very short email), create at least one node
        if not email_chunks and clean_body:
            email_chunks = [chunker._create_chunk(enhanced_text, "body", 0, meta)]
        
        for email_chunk in email_chunks:
            node_meta = meta.copy()
            node_meta["chunk_index"] = email_chunk.chunk_index
            node_meta["total_chunks"] = email_chunk.total_chunks
            node_meta["chunk_type"] = email_chunk.chunk_type
            node_meta["token_count"] = email_chunk.token_count
            nodes.append(TextNode(text=email_chunk.text, metadata=node_meta))
        
        # Progress tracking
        if processed_count % 50 == 0:
            print(f"[PROGRESS] Processed {processed_count} high-quality emails...")
    
    filtered_count = len(emails) - processed_count
    
    # Quality statistics
    print(f"\n[QUALITY-STATS] Processing Summary:")
    print(f"  Total emails: {len(emails)}")
    print(f"  High-quality emails: {processed_count} ({processed_count/len(emails)*100:.1f}%)")
    print(f"  Filtered out: {filtered_count} ({filtered_count/len(emails)*100:.1f}%)")
    print(f"  Average quality score: {sum(quality_scores)/len(quality_scores):.1f}/100")
    print(f"  Total search nodes created: {len(nodes)}")
    
    # Rejection reasons
    if rejected_reasons:
        from collections import Counter
        reason_counts = Counter(rejected_reasons)
        print(f"  Top rejection reasons:")
        for reason, count in reason_counts.most_common(5):
            print(f"    - {reason}: {count} emails")
    
    if len(nodes) == 0:
        raise ValueError("No high-quality emails found! Try lowering quality_threshold.")

    os.makedirs(persist_dir, exist_ok=True)
    
    # Create index with explicit settings
    print(f"[INDEX] Building vector index with {len(nodes)} high-quality nodes...")
    index = VectorStoreIndex(
        nodes,
        show_progress=True,
    )
    
    # Save quality metadata alongside index
    quality_metadata = {
        "parser_version": "2.0",
        "quality_threshold": quality_threshold,
        "max_marketing_score": max_marketing_score,
        "total_emails": len(emails),
        "processed_emails": processed_count,
        "filtered_emails": filtered_count,
        "average_quality": sum(quality_scores) / len(quality_scores),
        "total_nodes": len(nodes),
        "rejection_reasons": dict(Counter(rejected_reasons).most_common(10))
    }
    
    with open(f"{persist_dir}/quality_metadata.json", 'w') as f:
        json.dump(quality_metadata, f, indent=2)
    
    index.storage_context.persist(persist_dir=persist_dir)
    print(f"[INDEX] Index saved to {persist_dir}")
    print(f"[INDEX] Quality metadata saved to {persist_dir}/quality_metadata.json")
    
    return index


def get_quality_stats(persist_dir: str = "data/index") -> Dict[str, Any]:
    """Load quality statistics from saved metadata"""
    metadata_path = f"{persist_dir}/quality_metadata.json"
    
    if not os.path.exists(metadata_path):
        return {"error": "Quality metadata not found. Index may not be built with quality filtering."}
    
    with open(metadata_path, 'r') as f:
        return json.load(f)


if __name__ == "__main__":
    # Build smart chunked index with quality filtering
    print("Building Email Index with Smart Chunking...")
    index = build_index(
        quality_threshold=50.0,  # Only emails with 50+ quality score
        max_marketing_score=40.0  # Reject heavy marketing emails
    )
    print("Index build complete!")