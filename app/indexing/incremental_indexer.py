# app/indexing/incremental_indexer.py
import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from llama_index.core import VectorStoreIndex, StorageContext
from app.indexing.smart_chunker import SmartEmailChunker
from llama_index.core.schema import TextNode
import pickle

class IncrementalIndexer:
    """Intelligent incremental indexing system for improved performance"""
    
    def __init__(self, persist_dir: str = "data/index"):
        self.persist_dir = persist_dir
        self.metadata_file = os.path.join(persist_dir, "indexing_metadata.json")
        self.processed_emails_file = os.path.join(persist_dir, "processed_emails.pkl")
        # Use optimized smart chunker for high-quality embeddings
        self.chunker = SmartEmailChunker(
            min_chunk_size=50,
            max_chunk_size=384,
            overlap_size=30,
            preserve_paragraphs=True,
            preserve_sentences=True
        )
        
        # Load existing metadata
        self.metadata = self._load_metadata()
        self.processed_emails = self._load_processed_emails()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load indexing metadata"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load metadata: {e}")
        
        return {
            "last_update": None,
            "total_emails_indexed": 0,
            "total_nodes": 0,
            "source_files": {},
            "version": "1.0"
        }
    
    def _save_metadata(self):
        """Save indexing metadata"""
        os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
    
    def _load_processed_emails(self) -> Set[str]:
        """Load set of processed email IDs"""
        if os.path.exists(self.processed_emails_file):
            try:
                with open(self.processed_emails_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Warning: Could not load processed emails: {e}")
        
        return set()
    
    def _save_processed_emails(self):
        """Save set of processed email IDs"""
        os.makedirs(os.path.dirname(self.processed_emails_file), exist_ok=True)
        with open(self.processed_emails_file, 'wb') as f:
            pickle.dump(self.processed_emails, f)
    
    def _get_email_hash(self, email: Dict[str, Any]) -> str:
        """Generate unique hash for email to detect changes"""
        # Use message_id if available, otherwise hash content
        if email.get('message_id'):
            return email['message_id']
        
        # Create hash from key content
        content_for_hash = {
            'from': email.get('from', ''),
            'subject': email.get('subject', ''),
            'date': email.get('date', ''),
            'body': email.get('body', '')[:1000]  # First 1000 chars
        }
        
        content_str = json.dumps(content_for_hash, sort_keys=True)
        return hashlib.md5(content_str.encode()).hexdigest()
    
    def _get_source_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get source file information"""
        if not os.path.exists(file_path):
            return {}
        
        stat = os.stat(file_path)
        return {
            'path': file_path,
            'size': stat.st_size,
            'modified_time': stat.st_mtime,
            'hash': self._calculate_file_hash(file_path)
        }
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate hash of file for change detection"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def _file_needs_reprocessing(self, file_path: str) -> bool:
        """Check if file needs to be reprocessed"""
        current_info = self._get_source_file_info(file_path)
        stored_info = self.metadata['source_files'].get(file_path, {})
        
        # If no stored info, needs processing
        if not stored_info:
            return True
        
        # Check if file has been modified
        if current_info.get('modified_time') != stored_info.get('modified_time'):
            return True
        
        if current_info.get('hash') != stored_info.get('hash'):
            return True
        
        return False
    
    def get_new_emails(self, raw_path: str) -> List[Dict[str, Any]]:
        """Get only new or changed emails from raw file"""
        from app.indexing.build_index import _load_raw_emails
        
        # Check if file needs reprocessing
        if not self._file_needs_reprocessing(raw_path):
            print(f"📋 File {raw_path} hasn't changed, skipping...")
            return []
        
        # Load all emails from file
        try:
            all_emails = _load_raw_emails(raw_path)
        except Exception as e:
            print(f"❌ Error loading emails from {raw_path}: {e}")
            return []
        
        # Filter to only new emails
        new_emails = []
        for email in all_emails:
            email_hash = self._get_email_hash(email)
            if email_hash not in self.processed_emails:
                new_emails.append(email)
        
        print(f"📧 Found {len(new_emails)} new emails out of {len(all_emails)} total")
        return new_emails
    
    def build_incremental_index(self, raw_path: Optional[str] = None) -> Optional[VectorStoreIndex]:
        """Build index incrementally, only processing new emails"""
        from app.config.settings import get_settings
        from app.llm.provider import configure_llm
        from app.embeddings.provider import configure_embeddings
        from app.indexing.build_index import _resolve_latest_raw
        from app.ingest.mailparser_adapter import MailParserAdapter
        
        # Configure LLM and embeddings
        settings = get_settings()
        configure_llm(settings)
        configure_embeddings(settings)
        
        # Get raw file path
        try:
            raw_file = _resolve_latest_raw(raw_path)
        except FileNotFoundError as e:
            print(f"❌ {e}")
            return None
        
        print(f"🔄 Incremental indexing from: {raw_file}")
        
        # Get new emails only
        new_emails = self.get_new_emails(raw_file)
        
        if not new_emails:
            print("✅ Index is up to date!")
            # Load existing index if available
            try:
                if os.path.exists(os.path.join(self.persist_dir, "index_store.json")):
                    from llama_index.core import load_index_from_storage
                    storage_context = StorageContext.from_defaults(persist_dir=self.persist_dir)
                    return load_index_from_storage(storage_context)
            except Exception as e:
                print(f"Warning: Could not load existing index: {e}")
            return None
        
        # Process new emails into nodes using smart chunking
        parser = MailParserAdapter()
        new_nodes: List[TextNode] = []
        unique_senders = set()
        
        for i, email in enumerate(new_emails):
            # Parse email with quality analysis
            parsed = parser.parse_email_advanced(email)
            
            if len(parsed['clean_body'].strip()) < 20:
                continue
            
            sender_normalized = parsed['clean_sender'].lower()
            unique_senders.add(sender_normalized)
            
            # Enhanced metadata with quality scores
            meta = {
                "message_id": email.get("message_id"),
                "uid": email.get("uid"),
                "subject": parsed['clean_subject'],
                "from": parsed['clean_sender'],
                "from_normalized": sender_normalized,
                "date": email.get("date"),
                "sent_at": email.get("sent_at"),
                "folder": email.get("folder"),
                "email_index": self.metadata["total_emails_indexed"] + i,
                "indexed_at": datetime.now().isoformat(),
                "quality_score": parsed['quality_score'],
                "marketing_score": parsed['marketing_score'],
                "language_confidence": parsed['language_confidence']
            }
            
            # Add intelligence analysis if available
            try:
                from app.intelligence.email_analyzer import email_analyzer
                insights = email_analyzer.analyze_email(email)
                meta.update({
                    "importance_score": insights.importance_score,
                    "importance_level": insights.importance_level.name,
                    "categories": [cat.value for cat in insights.categories],
                    "sentiment_score": insights.sentiment_score,
                    "estimated_response_time": insights.estimated_response_time
                })
            except Exception as e:
                print(f"Warning: Could not analyze email intelligence: {e}")
            
            # Create enhanced text
            enhanced_text = f"From: {parsed['clean_sender']}\nSubject: {parsed['clean_subject']}\n\n{parsed['clean_body']}"
            
            # Smart chunking with context preservation
            content_dict = {
                'main_content': parsed['clean_body'],
                'cleaned_full_text': enhanced_text
            }
            
            email_chunks = self.chunker.chunk_email(content_dict, meta)
            
            for chunk in email_chunks:
                node_meta = meta.copy()
                node_meta["chunk_index"] = chunk.chunk_index
                node_meta["total_chunks"] = chunk.total_chunks
                node_meta["chunk_type"] = chunk.chunk_type
                node_meta["token_count"] = chunk.token_count
                new_nodes.append(TextNode(text=chunk.text, metadata=node_meta))
            
            # Mark email as processed
            email_hash = self._get_email_hash(email)
            self.processed_emails.add(email_hash)
        
        print(f"🔧 Created {len(new_nodes)} new nodes from {len(new_emails)} emails")
        print(f"👥 Unique senders in new emails: {len(unique_senders)}")
        
        # Load existing index or create new one
        index = None
        try:
            if os.path.exists(os.path.join(self.persist_dir, "index_store.json")):
                print("📖 Loading existing index...")
                storage_context = StorageContext.from_defaults(persist_dir=self.persist_dir)
                index = load_index_from_storage(storage_context)
                
                # Add new nodes to existing index
                print("🔄 Adding new nodes to existing index...")
                index.insert_nodes(new_nodes)
            else:
                print("🆕 Creating new index...")
                index = VectorStoreIndex(new_nodes, show_progress=True)
        
        except Exception as e:
            print(f"❌ Error updating index: {e}")
            print("🔄 Creating fresh index...")
            index = VectorStoreIndex(new_nodes, show_progress=True)
        
        # Save updated index
        os.makedirs(self.persist_dir, exist_ok=True)
        index.storage_context.persist(persist_dir=self.persist_dir)
        
        # Update metadata
        self.metadata.update({
            "last_update": datetime.now().isoformat(),
            "total_emails_indexed": self.metadata["total_emails_indexed"] + len(new_emails),
            "total_nodes": self.metadata["total_nodes"] + len(new_nodes),
            "source_files": {
                **self.metadata["source_files"],
                raw_file: self._get_source_file_info(raw_file)
            }
        })
        
        # Save metadata and processed emails
        self._save_metadata()
        self._save_processed_emails()
        
        print(f"✅ Incremental indexing complete!")
        print(f"📊 Total emails indexed: {self.metadata['total_emails_indexed']}")
        print(f"📊 Total nodes: {self.metadata['total_nodes']}")
        
        return index
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get comprehensive index statistics"""
        stats = {
            "last_update": self.metadata.get("last_update"),
            "total_emails_indexed": self.metadata.get("total_emails_indexed", 0),
            "total_nodes": self.metadata.get("total_nodes", 0),
            "processed_emails_count": len(self.processed_emails),
            "source_files": list(self.metadata.get("source_files", {}).keys()),
            "index_exists": os.path.exists(os.path.join(self.persist_dir, "index_store.json"))
        }
        
        return stats
    
    def rebuild_full_index(self, raw_path: Optional[str] = None) -> Optional[VectorStoreIndex]:
        """Rebuild index from scratch (useful for major updates)"""
        print("🔄 Rebuilding full index from scratch...")
        
        # Clear existing data
        self.processed_emails.clear()
        self.metadata = {
            "last_update": None,
            "total_emails_indexed": 0,
            "total_nodes": 0,
            "source_files": {},
            "version": "1.0"
        }
        
        # Remove existing index files
        if os.path.exists(self.persist_dir):
            import shutil
            try:
                shutil.rmtree(self.persist_dir)
            except Exception as e:
                print(f"Warning: Could not remove old index: {e}")
        
        # Build fresh index
        return self.build_incremental_index(raw_path)

    def add_emails(self, raw_file: str) -> Dict[str, Any]:
        """
        Simple method for EmailUpdater to add new emails to index.
        
        Args:
            raw_file: Path to JSON file with new emails
            
        Returns:
            Dict with results of the indexing operation
        """
        try:
            # Process the new emails using existing incremental logic
            result = self.update_index_incremental(raw_file)
            
            return {
                "success": True,
                "emails_processed": result.get('processed', 0),
                "emails_skipped": result.get('skipped', 0),
                "total_emails": result.get('total', 0)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "emails_processed": 0
            }

# Global incremental indexer instance
incremental_indexer = IncrementalIndexer()