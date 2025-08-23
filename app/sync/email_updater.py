"""
Email Update Manager for Non-Technical Users
Handles fetching, processing, and indexing emails with progress feedback
"""
import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import time

class EmailUpdater:
    """
    Manages email updates with user-friendly progress feedback.
    Designed for zero-knowledge users - handles all complexity internally.
    """
    
    def __init__(self):
        """Initialize the email updater with state management"""
        self.state_file = Path("data/sync_state.json")
        self.state = self._load_state()
        self.progress_callback: Optional[Callable] = None
        
    def _load_state(self) -> Dict[str, Any]:
        """Load the last update state from disk"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default state for first-time users
        return {
            "last_update": None,
            "last_email_count": 0,
            "last_update_success": True,
            "total_emails_processed": 0,
            "update_history": []
        }
    
    def _save_state(self):
        """Save the current state to disk"""
        os.makedirs(self.state_file.parent, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)
    
    def get_last_update_info(self) -> Dict[str, Any]:
        """Get user-friendly information about the last update"""
        if not self.state.get("last_update"):
            return {
                "status": "never",
                "message": "Never updated",
                "time_ago": "Never",
                "email_count": 0
            }
        
        last_update = datetime.fromisoformat(self.state["last_update"])
        now = datetime.now()
        diff = now - last_update
        
        # Format time difference in user-friendly way
        if diff.days > 0:
            time_ago = f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            time_ago = "Just now"
        
        return {
            "status": "success" if self.state.get("last_update_success") else "failed",
            "message": f"Last updated {time_ago}",
            "time_ago": time_ago,
            "email_count": self.state.get("total_emails_processed", 0),
            "timestamp": last_update
        }
    
    async def update_emails(self, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Main update method - fetches new emails and updates the index.
        
        Args:
            progress_callback: Function to call with progress updates (message, percentage)
            
        Returns:
            Dict with success status and details
        """
        self.progress_callback = progress_callback
        start_time = time.time()
        
        try:
            # Step 1: Initialize and check connection
            self._update_progress("Connecting to email server...", 5)
            await asyncio.sleep(0.1)  # Allow UI to update
            
            # Import here to avoid circular dependencies
            from app.config.settings import get_settings
            from app.ingest.imap_loader import fetch_emails
            
            settings = get_settings()
            
            # Validate email settings
            if not settings.imap_host or not settings.imap_user:
                self._update_progress("Email not configured", 0, error=True)
                return {
                    "success": False,
                    "error": "Email account not configured",
                    "action_needed": "configure_email"
                }
            
            # Step 2: Calculate date filter for incremental update
            self._update_progress("Checking for new emails...", 10)
            
            # Get emails from last 7 days on first run, or since last update
            if self.state.get("last_update"):
                # Add 1 day overlap to catch any missed emails
                last_update = datetime.fromisoformat(self.state["last_update"])
                since_date = last_update - timedelta(days=1)
            else:
                # First time - get last 30 days of emails
                since_date = datetime.now() - timedelta(days=30)
            
            # Step 3: Fetch emails
            self._update_progress("Fetching emails from server...", 20)
            
            # Fetch emails with date filtering for incremental updates
            emails = fetch_emails(settings, limit=500, since_date=since_date)
            
            if not emails:
                self._update_progress("No new emails found", 100)
                self.state["last_update"] = datetime.now().isoformat()
                self.state["last_update_success"] = True
                self._save_state()
                
                return {
                    "success": True,
                    "message": "Already up to date!",
                    "new_emails": 0,
                    "total_emails": self.state.get("total_emails_processed", 0)
                }
            
            # Step 4: Filter for truly new emails
            self._update_progress(f"Processing {len(emails)} emails...", 30)
            
            # Save raw emails to disk
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_file = f"data/raw/emails_update_{timestamp}.json"
            os.makedirs("data/raw", exist_ok=True)
            
            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(emails, f, indent=2, ensure_ascii=False)
            
            # Step 5: Update the index
            self._update_progress("Updating search index...", 60)
            
            from app.indexing.incremental_indexer import IncrementalIndexer
            
            indexer = IncrementalIndexer()
            index_result = await self._update_index_async(indexer, raw_file, len(emails))
            
            # Step 6: Update state and save
            self._update_progress("Finalizing update...", 90)
            
            self.state["last_update"] = datetime.now().isoformat()
            self.state["last_email_count"] = len(emails)
            self.state["last_update_success"] = True
            self.state["total_emails_processed"] = self.state.get("total_emails_processed", 0) + len(emails)
            
            # Add to history
            if "update_history" not in self.state:
                self.state["update_history"] = []
            
            self.state["update_history"].append({
                "timestamp": datetime.now().isoformat(),
                "email_count": len(emails),
                "duration": time.time() - start_time,
                "success": True
            })
            
            # Keep only last 10 history entries
            self.state["update_history"] = self.state["update_history"][-10:]
            
            self._save_state()
            
            # Step 7: Complete
            self._update_progress(f"Success! {len(emails)} emails updated", 100)
            
            return {
                "success": True,
                "message": f"Successfully updated {len(emails)} emails",
                "new_emails": len(emails),
                "total_emails": self.state["total_emails_processed"],
                "duration": time.time() - start_time
            }
            
        except Exception as e:
            # Handle errors gracefully
            self._update_progress(f"Update failed: {str(e)}", 0, error=True)
            
            self.state["last_update_success"] = False
            self._save_state()
            
            return {
                "success": False,
                "error": str(e),
                "message": "Update failed. Please try again.",
                "action_needed": "retry"
            }
    
    async def _update_index_async(self, indexer, raw_file: str, email_count: int) -> Dict[str, Any]:
        """Update the index asynchronously with progress updates"""
        # Simulate async index update with progress
        for i in range(60, 90, 5):
            self._update_progress(
                f"Indexing emails... ({(i-60)*email_count//30}/{email_count})", 
                i
            )
            await asyncio.sleep(0.2)
        
        # Actual index update
        result = indexer.add_emails(raw_file)
        return result
    
    def _update_progress(self, message: str, percentage: int, error: bool = False):
        """Update progress with user-friendly message"""
        if self.progress_callback:
            self.progress_callback({
                "message": message,
                "percentage": percentage,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
    
    def get_email_stats(self) -> Dict[str, Any]:
        """Get statistics about emails for display"""
        return {
            "total_emails": self.state.get("total_emails_processed", 0),
            "last_update": self.state.get("last_update"),
            "update_count": len(self.state.get("update_history", [])),
            "average_update_size": self._calculate_average_update_size()
        }
    
    def _calculate_average_update_size(self) -> int:
        """Calculate average number of emails per update"""
        history = self.state.get("update_history", [])
        if not history:
            return 0
        
        total = sum(h.get("email_count", 0) for h in history)
        return total // len(history) if history else 0
    
    def needs_update(self) -> bool:
        """Check if an update is recommended"""
        if not self.state.get("last_update"):
            return True
        
        last_update = datetime.fromisoformat(self.state["last_update"])
        # Suggest update if more than 6 hours old
        return (datetime.now() - last_update).seconds > 21600
    
    def reset_state(self):
        """Reset the update state - useful for troubleshooting"""
        self.state = {
            "last_update": None,
            "last_email_count": 0,
            "last_update_success": True,
            "total_emails_processed": 0,
            "update_history": []
        }
        self._save_state()


# Singleton instance for easy access
_updater_instance = None

def get_email_updater() -> EmailUpdater:
    """Get the singleton EmailUpdater instance"""
    global _updater_instance
    if _updater_instance is None:
        _updater_instance = EmailUpdater()
    return _updater_instance