# app/sync/sync_daemon.py
"""
Email Sync Daemon - Phase 3B
Run this to start live email synchronization in the background
"""

import time
import signal
import sys
from datetime import datetime

def signal_handler(sig, frame):
    """Handle shutdown gracefully"""
    print("\n[DAEMON] Shutting down...")
    sync_engine.stop()
    sys.exit(0)

def on_new_emails(results):
    """Callback when new emails are processed"""
    print(f"\n[NEW EMAILS] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Processed: {results['processed']}")
    print(f"  Added to index: {results['accepted']}")
    print(f"  Filtered out: {results['rejected']}")
    
    if results['high_quality']:
        print(f"  High quality emails:")
        for email in results['high_quality'][:3]:  # Show first 3
            print(f"    - {email['clean_subject'][:50]} (from {email['clean_sender']})")
    
    if results['low_quality']:
        print(f"  Rejected emails:")
        for email in results['low_quality'][:3]:  # Show first 3
            print(f"    - {email['subject'][:50]} ({email['rejection_reason']})")

def on_status_change(status):
    """Callback when sync status changes"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] Status: {status.current_status}")

def run_daemon():
    """Run the sync daemon"""
    print("=" * 60)
    print("EMAIL SYNC DAEMON - PHASE 3B")
    print("=" * 60)
    print("Starting live email synchronization...")
    print("Press Ctrl+C to stop\n")
    
    from app.sync.live_sync import get_sync_engine
    
    global sync_engine
    sync_engine = get_sync_engine()
    
    # Register callbacks
    sync_engine.register_new_email_callback(on_new_emails)
    sync_engine.register_status_change_callback(on_status_change)
    
    # Start sync
    if not sync_engine.start():
        print("[ERROR] Failed to start sync engine")
        return 1
    
    print(f"[DAEMON] Live sync is running")
    print(f"[DAEMON] Quality threshold: {sync_engine.quality_threshold}/100")
    print(f"[DAEMON] Max marketing score: {sync_engine.max_marketing_score}/100")
    print(f"[DAEMON] Sync interval: {sync_engine.sync_interval}s")
    print("")
    
    # Run until interrupted
    try:
        while True:
            # Print statistics every 60 seconds
            time.sleep(60)
            
            stats = sync_engine.get_statistics()
            print(f"\n[STATS] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Status: {stats['current_status']}")
            print(f"  Connection: {stats['connection_state']}")
            print(f"  Emails processed: {stats['emails_processed']}")
            print(f"  Emails added: {stats['emails_added']}")
            print(f"  Emails filtered: {stats['emails_filtered']}")
            print(f"  Total synced all-time: {stats['total_synced_all_time']}")
            
            if stats['last_sync']:
                print(f"  Last sync: {stats['last_sync']}")
            
            if stats['errors']:
                print(f"  Recent errors: {len(stats['errors'])}")
                for error in stats['errors'][-2:]:
                    print(f"    - {error}")
            
    except KeyboardInterrupt:
        pass
    
    # Cleanup
    sync_engine.stop()
    print("\n[DAEMON] Sync daemon stopped")
    return 0

if __name__ == "__main__":
    # Register signal handler for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    sys.exit(run_daemon())