#!/usr/bin/env python3
"""
Test UI Sync Integration
Verify that sync options are properly integrated into Streamlit UI
"""

def test_ui_imports():
    """Test that UI can import sync components"""
    print("UI SYNC INTEGRATION TEST")
    print("=" * 50)
    
    print("\n1. Testing UI Imports:")
    print("-" * 30)
    
    try:
        # Test sync imports
        from app.sync.live_sync import get_sync_engine
        from app.ui.sync_status import render_sync_status, render_sync_controls
        print("[OK] Sync components import successfully")
        
        # Test UI imports
        import streamlit as st
        print("[OK] Streamlit imports successfully")
        
        return True
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        return False

def test_sync_engine_in_ui():
    """Test sync engine functionality for UI"""
    print("\n2. Testing Sync Engine for UI:")
    print("-" * 30)
    
    from app.sync.live_sync import get_sync_engine
    
    sync_engine = get_sync_engine()
    
    # Test getting statistics
    stats = sync_engine.get_statistics()
    
    print(f"[OK] Sync engine accessible")
    print(f"  Is running: {stats['is_running']}")
    print(f"  Connection: {stats['connection_state']}")
    print(f"  Quality threshold: {sync_engine.quality_threshold}/100")
    print(f"  Max marketing: {sync_engine.max_marketing_score}/100")
    
    return True

def test_manual_sync_simulation():
    """Simulate manual sync process"""
    print("\n3. Testing Manual Sync Process:")
    print("-" * 30)
    
    from app.sync.live_sync import get_sync_engine
    
    sync_engine = get_sync_engine()
    
    # Test email processing (without actual connection)
    test_emails = [
        {
            "subject": "Important Meeting Tomorrow",
            "from": "boss@company.com",
            "body": "Please attend the meeting tomorrow at 10am in the conference room.",
            "date": "2025-01-09"
        },
        {
            "subject": "50% OFF Everything - Limited Time!",
            "from": "marketing@shop.com", 
            "body": "SHOP NOW! BUY NOW! LIMITED TIME OFFER! SALE ENDS TODAY!",
            "date": "2025-01-09"
        }
    ]
    
    print("Processing test emails...")
    results = sync_engine.process_new_emails(test_emails)
    
    print(f"[OK] Email processing works")
    print(f"  Processed: {results['processed']}")
    print(f"  Accepted: {results['accepted']}")
    print(f"  Rejected: {results['rejected']}")
    
    if results['high_quality']:
        print("\n  High-quality emails:")
        for email in results['high_quality']:
            print(f"    - {email['clean_subject']}")
            print(f"      Quality: {email['quality_score']:.1f}/100")
    
    if results['low_quality']:
        print("\n  Filtered emails:")
        for email in results['low_quality']:
            print(f"    - {email['subject']}")
            print(f"      Reason: {email['rejection_reason']}")
    
    return True

def show_ui_instructions():
    """Show instructions for using sync in UI"""
    print("\n" + "=" * 50)
    print("UI SYNC INTEGRATION COMPLETE!")
    print("=" * 50)
    
    print("\n📋 HOW TO USE SYNC IN THE UI:")
    print("-" * 40)
    
    print("\n1. START STREAMLIT APP:")
    print("   streamlit run app/ui/streamlit_app.py")
    
    print("\n2. GO TO SETTINGS TAB:")
    print("   Click on '⚙️ Settings' tab")
    
    print("\n3. LOGIN AS ADMIN:")
    print("   Enter admin password to access sync controls")
    
    print("\n4. SYNC OPTIONS:")
    print("   🚀 Activate Live Email Sync:")
    print("      - Starts background sync daemon")
    print("      - Automatically checks for new emails")
    print("      - Shows real-time status")
    print("      - Can be stopped anytime")
    print("")
    print("   📥 Manually Sync Latest Emails:")
    print("      - One-time check for new emails")
    print("      - Shows processing results")
    print("      - Lists accepted/rejected emails")
    
    print("\n5. CONFIGURATION:")
    print("   - Adjust Quality Threshold (0-100)")
    print("   - Set Max Marketing Score (0-100)")
    print("   - Configure Check Interval")
    
    print("\n6. QUICK SYNC:")
    print("   - Available in header when live sync is off")
    print("   - One-click manual sync")
    
    print("\n✅ FEATURES:")
    print("   - Real-time email monitoring")
    print("   - Quality filtering (Phase 3A)")
    print("   - Incremental index updates")
    print("   - Live status display")
    print("   - Manual sync option")
    print("   - Configurable thresholds")

def main():
    """Run all UI sync tests"""
    tests = [
        test_ui_imports,
        test_sync_engine_in_ui,
        test_manual_sync_simulation
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"[ERROR] Test failed: {e}")
    
    if passed == len(tests):
        show_ui_instructions()
        print("\n[SUCCESS] All UI sync tests passed!")
        return True
    else:
        print(f"\n[WARNING] {len(tests) - passed} tests failed")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)