# app/indexing/build_index.py
import os, glob, json
from typing import List, Dict, Any, Optional
from llama_index.core import VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from datetime import datetime

from app.config.settings import get_settings
from app.llm.provider import configure_llm
from app.embeddings.provider import configure_embeddings
from app.ingest.email_parser import CleanEmailParser


def _load_raw_emails(path: str) -> List[Dict[str, Any]]:
    """Load emails from .json, .jsonl, or .json.enc (encrypted) files."""
    from app.security.encryption import credential_manager
    
    emails: List[Dict[str, Any]] = []
    
    try:
        # Handle encrypted files
        if path.endswith(".json.enc"):
            print(f"🔓 Decrypting email file: {path}")
            with open(path, "r", encoding="utf-8") as f:
                encrypted_content = f.read().strip()
            
            # Decrypt the content
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


def _normalize_sender(sender: str) -> str:
    """Normalize sender field for better matching"""
    if not sender:
        return "unknown"
    
    # Extract just the name/org part, remove email addresses
    sender = sender.lower()
    
    # Remove email parts like <email@domain.com>
    import re
    sender = re.sub(r'<[^>]+>', '', sender).strip()
    
    # Remove quotes
    sender = sender.replace('"', '').replace("'", '')
    
    return sender.strip()


def build_index(raw_path: Optional[str] = None, persist_dir: str = "data/index") -> VectorStoreIndex:
    settings = get_settings()
    configure_llm(settings)
    configure_embeddings(settings)

    raw_file = _resolve_latest_raw(raw_path)
    print(f"[index] Using raw file: {raw_file}")

    emails = _load_raw_emails(raw_file)
    print(f"[index] Processing {len(emails)} emails")

    # Initialize email parser for HTML cleaning
    parser = CleanEmailParser()
    
    # Use smaller chunks for clean text
    splitter = SentenceSplitter(chunk_size=256, chunk_overlap=30)
    nodes: List[TextNode] = []
    
    # Track unique senders for debugging
    unique_senders = set()
    
    for i, e in enumerate(emails):
        # Extract clean text from body (handles HTML)
        body_raw = e.get("body") or ""
        
        # Clean the email body - automatically detects HTML
        if body_raw:
            # Determine content type
            content_type = "text/html" if "<html" in body_raw.lower() or "<body" in body_raw.lower() else "text/plain"
            text = parser.clean_email_body(body_raw, content_type)
        else:
            text = ""
            
        if not text or len(text.strip()) < 10:
            continue
        
        # Clean sender field
        sender_raw = e.get("from") or e.get("from_") or "unknown"
        sender = parser.clean_sender(sender_raw)
        sender_normalized = _normalize_sender(sender)
        unique_senders.add(sender_normalized)
        
        # Clean subject line
        subject = parser.clean_subject(e.get("subject") or "No subject")
        
        # Enhanced metadata with normalized fields
        meta = {
            "message_id": e.get("message_id"),
            "uid": e.get("uid"),
            "subject": subject,
            "from": sender,  # Keep original
            "from_normalized": sender_normalized,  # Add normalized version
            "date": e.get("date"),
            "sent_at": e.get("sent_at"),
            "folder": e.get("folder"),
            "email_index": i  # Track which email this came from
        }
        
        # Create a more informative text representation
        # Include metadata in the text for better semantic matching
        enhanced_text = f"From: {sender}\nSubject: {subject}\n\n{text}"
        
        # Split into chunks
        chunks = splitter.split_text(enhanced_text)
        
        # If no chunks (very short email), create at least one node
        if not chunks and text:
            chunks = [enhanced_text]
        
        for chunk_idx, ch in enumerate(chunks):
            node_meta = meta.copy()
            node_meta["chunk_index"] = chunk_idx
            node_meta["total_chunks"] = len(chunks)
            nodes.append(TextNode(text=ch, metadata=node_meta))
    
    print(f"[index] Created {len(nodes)} nodes from {len(emails)} emails")
    print(f"[index] Unique senders found: {len(unique_senders)}")
    print(f"[index] Sample senders: {list(unique_senders)[:10]}")

    os.makedirs(persist_dir, exist_ok=True)
    
    # Create index with explicit settings
    index = VectorStoreIndex(
        nodes,
        show_progress=True,
    )
    
    index.storage_context.persist(persist_dir=persist_dir)
    print(f"[index] Index saved to {persist_dir}")
    
    return index
