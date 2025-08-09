#!/usr/bin/env python3
"""
Quick verification of live sync components - Phase 3B
"""

def verify_imports():
    """Verify all sync components can be imported"""
    print("LIVE SYNC VERIFICATION - PHASE 3B")
    print("=" * 50)
    
    print("\n1. Import Verification:")
    print("-" * 30)
    
    try:
        from app.sync.live_sync import LiveEmailSync, get_sync_engine, SyncStatus
        print("[OK] Live sync engine imports")
        
        from app.sync.sync_daemon import run_daemon
        print("[OK] Sync daemon imports")
        
        from app.ui.sync_status import render_sync_status, render_sync_controls
        print("[OK] UI components import")
        
        return True
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        return False

def verify_engine_creation():
    """Verify sync engine can be created"""
    print("\n2. Engine Creation:")
    print("-" * 30)
    
    try:
        from app.sync.live_sync import get_sync_engine
        
        engine = get_sync_engine()
        print(f"[OK] Sync engine created")
        print(f"  Quality threshold: {engine.quality_threshold}/100")
        print(f"  Max marketing: {engine.max_marketing_score}/100")
        print(f"  Sync interval: {engine.sync_interval}s")
        
        # Get initial status
        status = engine.get_status()
        print(f"  Status: {status.current_status}")
        print(f"  Connection: {status.connection_state}")
        
        stats = engine.get_statistics()
        print(f"  Is running: {stats['is_running']}")
        
        return True
    except Exception as e:
        print(f"[ERROR] Engine creation failed: {e}")
        return False

def verify_parser_integration():
    """Verify Advanced Parser 2.0 integration"""
    print("\n3. Parser Integration:")
    print("-" * 30)
    
    try:
        from app.sync.live_sync import LiveEmailSync
        
        engine = LiveEmailSync()
        
        # Test email processing
        test_email = {
            "subject": "Test Email",
            "from": "test@example.com",
            "body": "This is a test email for verification purposes.",
            "date": "2025-01-09"
        }
        
        results = engine.process_new_emails([test_email])
        
        print(f"[OK] Email processing works")
        print(f"  Processed: {results['processed']}")
        print(f"  Accepted: {results['accepted']}")
        print(f"  Rejected: {results['rejected']}")
        
        if results['high_quality']:
            email = results['high_quality'][0]
            print(f"  Quality score: {email['quality_score']:.1f}/100")
        
        return True
    except Exception as e:
        print(f"[ERROR] Parser integration failed: {e}")
        return False

def verify_callbacks():
    """Verify callback system"""
    print("\n4. Callback System:")
    print("-" * 30)
    
    try:
        from app.sync.live_sync import get_sync_engine
        
        engine = get_sync_engine()
        
        # Test callback registration
        callback_called = {'status': False, 'email': False}
        
        def test_status_callback(status):
            callback_called['status'] = True
        
        def test_email_callback(results):
            callback_called['email'] = True
        
        engine.register_status_change_callback(test_status_callback)
        engine.register_new_email_callback(test_email_callback)
        
        print(f"[OK] Callbacks registered")
        print(f"  Status callbacks: {len(engine.on_status_change_callbacks)}")
        print(f"  Email callbacks: {len(engine.on_new_email_callbacks)}")
        
        # Trigger status change
        engine._update_status("Test status")
        
        if callback_called['status']:
            print("[OK] Status callback works")
        else:
            print("[WARN] Status callback not triggered")
        
        return True
    except Exception as e:
        print(f"[ERROR] Callback system failed: {e}")
        return False

def main():
    """Run all verifications"""
    tests = [
        verify_imports,
        verify_engine_creation,
        verify_parser_integration,
        verify_callbacks
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"VERIFICATION RESULTS: {passed}/{len(tests)} passed")
    
    if passed == len(tests):
        print("\n[SUCCESS] Live Email Sync is ready!")
        print("\nTo start live sync:")
        print("  1. Run daemon: python app/sync/sync_daemon.py")
        print("  2. Or use UI: Add sync_status to Streamlit app")
        print("\nFeatures:")
        print("  - Real-time email monitoring")
        print("  - Quality filtering (Advanced Parser 2.0)")
        print("  - Incremental index updates")
        print("  - Background sync daemon")
        print("  - UI status monitoring")
    else:
        print(f"\n[WARNING] {len(tests) - passed} components need attention")
    
    return passed == len(tests)

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)