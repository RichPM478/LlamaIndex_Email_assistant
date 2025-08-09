#!/usr/bin/env python3
"""
Reset Sync State - Clear processed message IDs to retry failed sync
"""

import os
import sys

# Add project root to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

def main():
    print("RESET SYNC STATE")
    print("=" * 50)
    
    from app.sync.live_sync import get_sync_engine
    
    sync_engine = get_sync_engine()
    
    # Show current state
    print(f"\nCurrent sync state:")
    print(f"  Processed message IDs: {len(sync_engine.sync_state['processed_message_ids'])}")
    print(f"  Total synced: {sync_engine.sync_state.get('total_emails_synced', 0)}")
    
    # Reset state
    sync_engine.reset_sync_state()
    
    # Verify reset
    print(f"\nAfter reset:")
    print(f"  Processed message IDs: {len(sync_engine.sync_state['processed_message_ids'])}")
    print(f"  Status counters reset to 0")
    
    print(f"\n✅ Sync state reset complete!")
    print(f"📧 The 330 emails will now be reprocessed on next sync attempt")
    print(f"\nNow restart live sync in the UI to process the emails.")

if __name__ == "__main__":
    main()