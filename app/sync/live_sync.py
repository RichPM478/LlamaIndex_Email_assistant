# app/sync/live_sync.py
"""
Live Email Sync Engine - Phase 3B

Features:
- IMAP IDLE support for real-time notifications
- Incremental email fetching (only new emails)
- Quality filtering with Advanced Parser 2.0
- Smart indexing to avoid reprocessing
- Background sync daemon
- Conflict resolution for updates
"""

import imaplib
import email
import time
import threading
import queue
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import hashlib

from app.config.settings import get_settings
from app.ingest.mailparser_adapter import MailParserAdapter
from app.indexing.quality_indexer import build_quality_index

@dataclass
class SyncStatus:
    """Real-time sync status tracking"""
    is_running: bool = False
    last_sync: Optional[datetime] = None
    last_check: Optional[datetime] = None
    emails_processed: int = 0
    emails_added: int = 0
    emails_filtered: int = 0
    current_status: str = "Idle"
    errors: List[str] = None
    connection_state: str = "Disconnected"
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class LiveEmailSync:
    """
    Real-time email synchronization engine with IMAP IDLE support
    
    Features:
    - Monitors inbox for new emails in real-time
    - Quality filtering before indexing
    - Incremental updates to search index
    - Automatic reconnection on failure
    """
    
    def __init__(self, 
                 quality_threshold: float = 50.0,
                 max_marketing_score: float = 40.0,
                 sync_interval: int = 120,  # Check every 2 minutes (more reasonable)
                 persist_dir: str = "data/index",
                 state_file: str = "data/sync_state.json"):
        
        self.settings = get_settings()
        self.quality_threshold = quality_threshold
        self.max_marketing_score = max_marketing_score
        self.sync_interval = sync_interval
        self.persist_dir = persist_dir
        self.state_file = state_file
        
        # Components
        self.parser = MailParserAdapter()
        self.imap_connection = None
        self.status = SyncStatus()
        
        # Threading
        self.sync_thread = None
        self.stop_event = threading.Event()
        self.email_queue = queue.Queue()
        
        # Callbacks
        self.on_new_email_callbacks = []
        self.on_status_change_callbacks = []
        
        # Load sync state
        self.sync_state = self._load_sync_state()
    
    def _load_sync_state(self) -> Dict[str, Any]:
        """Load persistent sync state"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[SYNC] Error loading state: {e}")
        
        return {
            "last_uid": 0,
            "processed_message_ids": [],
            "last_sync_time": None,
            "total_emails_synced": 0
        }
    
    def _save_sync_state(self):
        """Save sync state to disk"""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.sync_state, f, indent=2, default=str)
        except Exception as e:
            print(f"[SYNC] Error saving state: {e}")
    
    def connect(self) -> bool:
        """Establish IMAP connection"""
        try:
            print(f"[SYNC] Connecting to {self.settings.imap_host}:{self.settings.imap_port}...")
            
            if self.settings.imap_ssl:
                self.imap_connection = imaplib.IMAP4_SSL(
                    self.settings.imap_host, 
                    self.settings.imap_port
                )
            else:
                self.imap_connection = imaplib.IMAP4(
                    self.settings.imap_host,
                    self.settings.imap_port
                )
            
            # Login
            self.imap_connection.login(
                self.settings.imap_user,
                self.settings.imap_password
            )
            
            # Select folder
            folder = self.settings.imap_folder or "INBOX"
            self.imap_connection.select(folder)
            
            self.status.connection_state = "Connected"
            self._update_status("Connected to email server")
            
            print(f"[SYNC] Successfully connected to {folder}")
            return True
            
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            print(f"[SYNC] {error_msg}")
            self.status.errors.append(error_msg)
            self.status.connection_state = "Failed"
            self._update_status(error_msg)
            return False
    
    def check_idle_support(self) -> bool:
        """Check if server supports IMAP IDLE"""
        try:
            if hasattr(self.imap_connection, 'capabilities'):
                capabilities = self.imap_connection.capabilities
                return b'IDLE' in capabilities
            return False
        except:
            return False
    
    def fetch_new_emails(self) -> List[Dict[str, Any]]:
        """Fetch only new emails since last sync with batching and reconnection"""
        new_emails = []
        
        # Always connect fresh for each sync to avoid timeout issues
        if not self.connect():
            return new_emails
        
        try:
            # Search for new emails
            if self.sync_state["last_uid"] > 0:
                # Get emails after last known UID
                search_criteria = f'UID {self.sync_state["last_uid"]+1}:*'
                typ, data = self.imap_connection.uid('search', None, search_criteria)
            else:
                # Get recent emails from last 7 days for initial sync
                date = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
                typ, data = self.imap_connection.search(None, f'(SINCE {date})')
            
            if typ != 'OK':
                return new_emails
            
            email_ids = data[0].split()
            
            print(f"[SYNC] Found {len(email_ids)} potential new emails")
            
            if len(email_ids) > 100:
                print(f"[SYNC] Large batch detected, processing in chunks...")
            
            # Process emails in batches to prevent timeouts
            batch_size = 50
            processed_count = 0
            
            for i in range(0, len(email_ids), batch_size):
                batch_ids = email_ids[i:i + batch_size]
                print(f"[SYNC] Processing batch {i//batch_size + 1}/{(len(email_ids) + batch_size - 1)//batch_size} ({len(batch_ids)} emails)")
                
                for email_id in batch_ids:
                    try:
                        # Check connection health every 10 emails
                        if processed_count % 10 == 0:
                            try:
                                self.imap_connection.noop()  # Keep connection alive
                            except Exception as e:
                                print(f"[SYNC] Connection check failed, reconnecting: {e}")
                                if not self.connect():
                                    print(f"[SYNC] Reconnection failed, stopping fetch")
                                    break
                        
                        # Fetch email with timeout handling
                        if self.sync_state["last_uid"] > 0:
                            typ, msg_data = self.imap_connection.uid('fetch', email_id, '(RFC822)')
                        else:
                            typ, msg_data = self.imap_connection.fetch(email_id, '(RFC822)')
                        
                        if typ != 'OK':
                            continue
                        
                        # Parse email
                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email)
                        
                        # Extract message ID
                        message_id = msg.get('Message-ID', '')
                        
                        # Check if already processed
                        if message_id and message_id in self.sync_state["processed_message_ids"]:
                            continue
                        
                        # Extract email data
                        email_data = self._extract_email_data(msg)
                        
                        # Add UID for tracking
                        if self.sync_state["last_uid"] > 0:
                            email_data['uid'] = int(email_id)
                        
                        new_emails.append(email_data)
                        processed_count += 1
                        
                        # Track message ID
                        if message_id:
                            self.sync_state["processed_message_ids"].append(message_id)
                            # Keep only last 10000 message IDs to prevent memory issues
                            if len(self.sync_state["processed_message_ids"]) > 10000:
                                self.sync_state["processed_message_ids"] = self.sync_state["processed_message_ids"][-10000:]
                        
                        # Update last UID
                        if 'uid' in email_data and email_data['uid'] > self.sync_state["last_uid"]:
                            self.sync_state["last_uid"] = email_data['uid']
                        
                        # Progress update for large batches
                        if processed_count % 25 == 0:
                            print(f"[SYNC] Progress: {processed_count}/{len(email_ids)} emails processed")
                        
                    except Exception as e:
                        print(f"[SYNC] Error processing email {email_id}: {e}")
                        # Try to reconnect on socket errors
                        if "socket error" in str(e).lower() or "eof" in str(e).lower():
                            print(f"[SYNC] Socket error detected, attempting reconnection...")
                            if not self.connect():
                                print(f"[SYNC] Failed to reconnect, stopping batch")
                                break
                        continue
                
                # Brief pause between batches to prevent overwhelming server
                if i + batch_size < len(email_ids):
                    time.sleep(0.5)
            
            print(f"[SYNC] Successfully processed {processed_count} emails")
            return new_emails
            
        except Exception as e:
            print(f"[SYNC] Error fetching emails: {e}")
            self.status.errors.append(f"Fetch error: {str(e)}")
            
            # Try reconnecting on connection errors
            if "socket error" in str(e).lower() or "eof" in str(e).lower() or "connection" in str(e).lower():
                print(f"[SYNC] Attempting to reconnect after error...")
                if self.connect():
                    print(f"[SYNC] Reconnected successfully, try fetching again")
                else:
                    print(f"[SYNC] Reconnection failed")
            
            return new_emails
    
    def _extract_email_data(self, msg) -> Dict[str, Any]:
        """Extract email data from message object"""
        # Get body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode('utf-8', errors='ignore')
                        break
                elif part.get_content_type() == "text/html" and not body:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode('utf-8', errors='ignore')
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode('utf-8', errors='ignore')
        
        return {
            "message_id": msg.get('Message-ID', ''),
            "from": msg.get('From', ''),
            "subject": msg.get('Subject', ''),
            "date": msg.get('Date', ''),
            "body": body,
            "sent_at": datetime.now().isoformat()
        }
    
    def process_new_emails(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process new emails with quality filtering"""
        results = {
            "processed": 0,
            "accepted": 0,
            "rejected": 0,
            "high_quality": [],
            "low_quality": []
        }
        
        for email_data in emails:
            # Parse with Advanced Parser 2.0
            parsed = self.parser.parse_email_advanced(email_data)
            
            # Quality check
            if (parsed['quality_score'] >= self.quality_threshold and 
                parsed['marketing_score'] <= self.max_marketing_score):
                
                results["accepted"] += 1
                results["high_quality"].append({
                    **email_data,
                    **parsed,
                    "sync_time": datetime.now().isoformat()
                })
            else:
                results["rejected"] += 1
                results["low_quality"].append({
                    "subject": parsed['clean_subject'],
                    "from": parsed['clean_sender'],
                    "quality_score": parsed['quality_score'],
                    "rejection_reason": self._get_rejection_reason(parsed)
                })
            
            results["processed"] += 1
        
        return results
    
    def _get_rejection_reason(self, parsed: Dict[str, Any]) -> str:
        """Determine why an email was rejected"""
        if parsed['quality_score'] < self.quality_threshold:
            return f"Low quality ({parsed['quality_score']:.1f} < {self.quality_threshold})"
        elif parsed['marketing_score'] > self.max_marketing_score:
            return f"High marketing ({parsed['marketing_score']:.1f} > {self.max_marketing_score})"
        else:
            return "Other quality issues"
    
    def update_index_incremental(self, high_quality_emails: List[Dict[str, Any]]):
        """Update search index with new high-quality emails"""
        if not high_quality_emails:
            return
        
        try:
            from llama_index.core import StorageContext, load_index_from_storage, VectorStoreIndex
            from llama_index.core.node_parser import SentenceSplitter
            from llama_index.core.schema import TextNode
            from app.config.settings import get_settings
            from app.llm.provider import configure_llm
            from app.embeddings.provider import configure_embeddings
            
            # Configure models
            settings = get_settings()
            configure_llm(settings)
            configure_embeddings(settings)
            
            # Load existing index
            storage_context = StorageContext.from_defaults(persist_dir=self.persist_dir)
            index = load_index_from_storage(storage_context)
            
            # Create nodes for new emails
            splitter = SentenceSplitter(chunk_size=256, chunk_overlap=30)
            new_nodes = []
            
            for email_data in high_quality_emails:
                # Create enhanced text
                enhanced_text = f"From: {email_data['clean_sender']}\nSubject: {email_data['clean_subject']}\n\n{email_data['clean_body']}"
                
                # Split into chunks
                chunks = splitter.split_text(enhanced_text)
                
                for chunk_idx, chunk in enumerate(chunks):
                    node = TextNode(
                        text=chunk,
                        metadata={
                            "message_id": email_data.get("message_id"),
                            "subject": email_data['clean_subject'],
                            "from": email_data['clean_sender'],
                            "date": email_data.get("date"),
                            "quality_score": email_data['quality_score'],
                            "sync_time": email_data.get("sync_time"),
                            "chunk_index": chunk_idx,
                            "total_chunks": len(chunks)
                        }
                    )
                    new_nodes.append(node)
            
            # Add new nodes to index
            print(f"[SYNC] Adding {len(new_nodes)} nodes to index...")
            
            # Use the correct method to add nodes to existing index
            try:
                # Method 1: Try using refresh with new nodes
                index.refresh_ref_docs(new_nodes)
            except Exception as e1:
                try:
                    # Method 2: Try using insert_nodes 
                    index.insert_nodes(new_nodes)
                except Exception as e2:
                    # Method 3: Rebuild index with all nodes (fallback)
                    print(f"[SYNC] Direct insertion failed, rebuilding index section...")
                    
                    # Get existing nodes from docstore
                    existing_nodes = list(index.docstore.docs.values())
                    all_nodes = existing_nodes + new_nodes
                    
                    # Create new index with all nodes
                    new_index = VectorStoreIndex(all_nodes)
                    
                    # Replace storage context
                    index = new_index
            
            # Persist updated index
            index.storage_context.persist(persist_dir=self.persist_dir)
            
            print(f"[SYNC] Added {len(new_nodes)} nodes from {len(high_quality_emails)} emails to index")
            
        except Exception as e:
            print(f"[SYNC] Error updating index: {e}")
            self.status.errors.append(f"Index update error: {str(e)}")
    
    def _sync_loop(self):
        """Main sync loop - periodic polling with user-friendly intervals"""
        print("[SYNC] Starting periodic sync loop...")
        
        while not self.stop_event.is_set():
            try:
                self.status.last_check = datetime.now()
                
                # Check for new emails
                self._update_status("Checking for new emails...")
                new_emails = self.fetch_new_emails()
                
                if new_emails:
                    print(f"[SYNC] Processing {len(new_emails)} new emails...")
                    self._update_status(f"Processing {len(new_emails)} new emails...")
                    
                    # Process with quality filtering
                    results = self.process_new_emails(new_emails)
                    
                    # Update statistics
                    self.status.emails_processed += results["processed"]
                    self.status.emails_added += results["accepted"]
                    self.status.emails_filtered += results["rejected"]
                    
                    # Update index with high-quality emails
                    if results["high_quality"]:
                        self._update_status(f"Updating index with {len(results['high_quality'])} emails...")
                        self.update_index_incremental(results["high_quality"])
                    
                    # Notify callbacks
                    for callback in self.on_new_email_callbacks:
                        try:
                            callback(results)
                        except Exception as e:
                            print(f"[SYNC] Callback error: {e}")
                    
                    # Save state
                    self.sync_state["last_sync_time"] = datetime.now().isoformat()
                    self.sync_state["total_emails_synced"] += results["accepted"]
                    self._save_sync_state()
                    
                    self.status.last_sync = datetime.now()
                    self._update_status(f"✅ Synced {results['accepted']} emails ({results['rejected']} filtered)")
                    
                    # Close connection after successful sync to prevent timeout issues
                    if self.imap_connection:
                        try:
                            self.imap_connection.logout()
                        except:
                            pass
                        self.imap_connection = None
                        self.status.connection_state = "Disconnected"
                else:
                    self._update_status("📭 No new emails found")
                    
                    # Close connection if no new emails to prevent timeouts
                    if self.imap_connection:
                        try:
                            self.imap_connection.logout()
                        except:
                            pass
                        self.imap_connection = None
                        self.status.connection_state = "Disconnected"
                
                # Wait before next check (much more reasonable interval)
                wait_time = self.sync_interval
                for remaining in range(wait_time, 0, -5):
                    if self.stop_event.is_set():
                        break
                    self._update_status(f"💤 Next check in {remaining}s...")
                    self.stop_event.wait(5)  # Check every 5 seconds if we should stop
                
            except Exception as e:
                print(f"[SYNC] Sync loop error: {e}")
                self.status.errors.append(f"Sync error: {str(e)}")
                
                # Clean up connection on error
                if self.imap_connection:
                    try:
                        self.imap_connection.logout()
                    except:
                        pass
                    self.imap_connection = None
                    self.status.connection_state = "Error"
                
                # Wait before retry with countdown
                self._update_status("❌ Error occurred, retrying in 30s...")
                for remaining in range(30, 0, -5):
                    if self.stop_event.is_set():
                        break
                    self._update_status(f"❌ Retrying in {remaining}s...")
                    self.stop_event.wait(5)
    
    def _update_status(self, status: str):
        """Update current status and notify callbacks"""
        self.status.current_status = status
        print(f"[SYNC] {status}")  # Also log to console for visibility
        
        for callback in self.on_status_change_callbacks:
            try:
                callback(self.status)
            except Exception as e:
                print(f"[SYNC] Status callback error: {e}")
    
    def start(self) -> bool:
        """Start live sync in background"""
        if self.status.is_running:
            print("[SYNC] Already running")
            return False
        
        # Connect to server
        if not self.connect():
            return False
        
        # Start sync thread
        self.stop_event.clear()
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        
        self.status.is_running = True
        self._update_status("Live sync started")
        
        print("[SYNC] Live sync started successfully")
        return True
    
    def stop(self):
        """Stop live sync"""
        if not self.status.is_running:
            return
        
        print("[SYNC] Stopping live sync...")
        
        # Signal thread to stop
        self.stop_event.set()
        
        # Wait for thread to finish
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        
        # Close IMAP connection
        if self.imap_connection:
            try:
                self.imap_connection.logout()
            except:
                pass
            self.imap_connection = None
        
        self.status.is_running = False
        self.status.connection_state = "Disconnected"
        self._update_status("Live sync stopped")
        
        print("[SYNC] Live sync stopped")
    
    def register_new_email_callback(self, callback: Callable):
        """Register callback for new email notifications"""
        self.on_new_email_callbacks.append(callback)
    
    def register_status_change_callback(self, callback: Callable):
        """Register callback for status changes"""
        self.on_status_change_callbacks.append(callback)
    
    def get_status(self) -> SyncStatus:
        """Get current sync status"""
        return self.status
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get sync statistics"""
        return {
            "is_running": self.status.is_running,
            "connection_state": self.status.connection_state,
            "last_sync": self.status.last_sync.isoformat() if self.status.last_sync else None,
            "last_check": self.status.last_check.isoformat() if self.status.last_check else None,
            "emails_processed": self.status.emails_processed,
            "emails_added": self.status.emails_added,
            "emails_filtered": self.status.emails_filtered,
            "current_status": self.status.current_status,
            "total_synced_all_time": self.sync_state.get("total_emails_synced", 0),
            "errors": self.status.errors[-5:] if self.status.errors else []  # Last 5 errors
        }
    
    def reset_sync_state(self):
        """Reset sync state to allow reprocessing of emails"""
        print("[SYNC] Resetting sync state to retry failed emails...")
        
        # Clear processed message IDs to allow reprocessing
        self.sync_state["processed_message_ids"] = []
        
        # Reset counters
        self.status.emails_processed = 0
        self.status.emails_added = 0
        self.status.emails_filtered = 0
        
        # Save state
        self._save_sync_state()
        
        print("[SYNC] Sync state reset - emails will be reprocessed on next sync")

# Global sync instance
_sync_engine = None

def get_sync_engine() -> LiveEmailSync:
    """Get or create global sync engine"""
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = LiveEmailSync()
    return _sync_engine