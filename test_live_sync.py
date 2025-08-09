#!/usr/bin/env python3
"""
Test Live Email Sync - Phase 3B
"""

import time
from datetime import datetime

def test_sync_connection():
    """Test basic sync engine connection"""
    print("LIVE EMAIL SYNC TEST - PHASE 3B")
    print("=" * 60)
    
    from app.sync.live_sync import get_sync_engine
    
    sync_engine = get_sync_engine()
    
    print("\n1. CONNECTION TEST")
    print("-" * 40)
    
    # Test connection
    print("Attempting to connect to email server...")
    if sync_engine.connect():
        print("[SUCCESS] Connected to email server")
        
        # Check IDLE support
        idle_support = sync_engine.check_idle_support()
        if idle_support:
            print("[INFO] Server supports IMAP IDLE (real-time notifications)")
        else:
            print(f"[INFO] Server doesn't support IDLE (will poll every {sync_engine.sync_interval}s)")
        
        return True
    else:
        print("[ERROR] Failed to connect")
        errors = sync_engine.get_statistics()['errors']
        if errors:
            print("Errors:")
            for error in errors:
                print(f"  - {error}")
        return False

def test_fetch_emails():
    """Test fetching new emails"""
    print("\n2. EMAIL FETCH TEST")
    print("-" * 40)
    
    from app.sync.live_sync import get_sync_engine
    
    sync_engine = get_sync_engine()
    
    if not sync_engine.connect():
        print("[SKIP] Cannot test without connection")
        return False
    
    print("Fetching recent emails...")
    new_emails = sync_engine.fetch_new_emails()
    
    print(f"Found {len(new_emails)} emails")
    
    if new_emails:
        # Show first 5
        print("\nSample emails:")
        for i, email in enumerate(new_emails[:5], 1):
            print(f"  {i}. {email.get('subject', 'No subject')[:50]}...")
            print(f"     From: {email.get('from', 'Unknown')[:50]}")
    
    return True

def test_quality_filtering():
    """Test quality filtering on fetched emails"""
    print("\n3. QUALITY FILTERING TEST")
    print("-" * 40)
    
    from app.sync.live_sync import get_sync_engine
    
    sync_engine = get_sync_engine()
    
    if not sync_engine.connect():
        print("[SKIP] Cannot test without connection")
        return False
    
    # Fetch emails
    new_emails = sync_engine.fetch_new_emails()
    
    if not new_emails:
        print("[SKIP] No emails to test")
        return True
    
    # Test first 10 emails
    test_emails = new_emails[:10]
    print(f"Processing {len(test_emails)} emails with quality filtering...")
    
    results = sync_engine.process_new_emails(test_emails)
    
    print(f"\nResults:")
    print(f"  Processed: {results['processed']}")
    print(f"  Accepted (high quality): {results['accepted']}")
    print(f"  Rejected (low quality): {results['rejected']}")
    
    if results['accepted'] > 0:
        acceptance_rate = (results['accepted'] / results['processed']) * 100
        print(f"  Acceptance rate: {acceptance_rate:.1f}%")
    
    if results['high_quality']:
        print(f"\nHigh quality emails:")
        for email in results['high_quality'][:3]:
            print(f"  - {email['clean_subject'][:50]}...")
            print(f"    Quality: {email['quality_score']:.1f}/100")
            print(f"    From: {email['clean_sender']}")
    
    if results['low_quality']:
        print(f"\nRejected emails:")
        for email in results['low_quality'][:3]:
            print(f"  - {email['subject'][:50]}...")
            print(f"    Reason: {email['rejection_reason']}")
    
    return True

def test_sync_daemon():
    """Test sync daemon functionality"""
    print("\n4. SYNC DAEMON TEST")
    print("-" * 40)
    
    from app.sync.live_sync import get_sync_engine
    
    sync_engine = get_sync_engine()
    
    # Define test callbacks
    email_count = {'count': 0}
    
    def on_new_emails(results):
        email_count['count'] += results['accepted']
        print(f"  [CALLBACK] New emails: {results['accepted']} accepted, {results['rejected']} rejected")
    
    def on_status_change(status):
        print(f"  [STATUS] {status.current_status}")
    
    # Register callbacks
    sync_engine.register_new_email_callback(on_new_emails)
    sync_engine.register_status_change_callback(on_status_change)
    
    print("Starting sync daemon...")
    if not sync_engine.start():
        print("[ERROR] Failed to start daemon")
        return False
    
    print("[SUCCESS] Daemon started")
    
    # Run for 10 seconds
    print("Running for 10 seconds to test functionality...")
    time.sleep(10)
    
    # Get statistics
    stats = sync_engine.get_statistics()
    print(f"\nStatistics after 10 seconds:")
    print(f"  Status: {stats['current_status']}")
    print(f"  Connection: {stats['connection_state']}")
    print(f"  Emails processed: {stats['emails_processed']}")
    print(f"  Emails added: {stats['emails_added']}")
    print(f"  Emails filtered: {stats['emails_filtered']}")
    
    # Stop daemon
    print("\nStopping daemon...")
    sync_engine.stop()
    print("[SUCCESS] Daemon stopped")
    
    return True

def test_incremental_indexing():
    """Test incremental index updates"""
    print("\n5. INCREMENTAL INDEXING TEST")
    print("-" * 40)
    
    from app.sync.live_sync import get_sync_engine
    import os
    
    sync_engine = get_sync_engine()
    
    # Check if index exists
    if not os.path.exists(sync_engine.persist_dir):
        print("[SKIP] No index found. Run quality indexer first.")
        return True
    
    if not sync_engine.connect():
        print("[SKIP] Cannot test without connection")
        return False
    
    # Fetch and process emails
    new_emails = sync_engine.fetch_new_emails()
    
    if not new_emails:
        print("[SKIP] No new emails to index")
        return True
    
    # Process first email
    test_email = new_emails[:1]
    results = sync_engine.process_new_emails(test_email)
    
    if results['high_quality']:
        print(f"Adding {len(results['high_quality'])} high-quality email to index...")
        
        try:
            sync_engine.update_index_incremental(results['high_quality'])
            print("[SUCCESS] Index updated successfully")
            return True
        except Exception as e:
            print(f"[ERROR] Index update failed: {e}")
            return False
    else:
        print("[SKIP] No high-quality emails to add")
        return True

def main():
    """Run all live sync tests"""
    print("=" * 60)
    print("PHASE 3B: LIVE EMAIL SYNC TESTING")
    print("=" * 60)
    
    tests = [
        ("Connection", test_sync_connection),
        ("Email Fetch", test_fetch_emails),
        ("Quality Filtering", test_quality_filtering),
        ("Sync Daemon", test_sync_daemon),
        ("Incremental Indexing", test_incremental_indexing)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            print(f"\nRunning: {name}")
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"[ERROR] Test failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n[SUCCESS] All live sync tests passed!")
        print("Phase 3B: Live Email Sync is ready!")
    else:
        print(f"\n[WARNING] {failed} tests failed")
    
    return failed == 0

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)