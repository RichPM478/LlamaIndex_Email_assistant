"""
Complete Index Rebuild with Fixed Metadata
This script will rebuild the entire email index with proper metadata extraction
"""
import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path

# Set encoding for Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, str(Path(__file__).parent))

def clear_old_index():
    """Clear all old index files and caches"""
    print("=" * 60)
    print("STEP 1: Clearing Old Index")
    print("=" * 60)
    
    # Directories to clear
    dirs_to_clear = [
        "data/index",
        "data/flexible_index",
        "__pycache__",
        "app/__pycache__",
        "app/indexing/__pycache__"
    ]
    
    for dir_path in dirs_to_clear:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"  [OK] Cleared: {dir_path}")
            except Exception as e:
                print(f"  [WARN] Could not clear {dir_path}: {e}")
    
    # Clear sync state to force full re-fetch
    sync_state_file = "data/sync_state.json"
    if os.path.exists(sync_state_file):
        os.remove(sync_state_file)
        print(f"  [OK] Cleared sync state")
    
    print("\n[SUCCESS] Old index and caches cleared")

def fetch_all_emails_with_metadata():
    """Fetch all emails with proper metadata extraction"""
    print("\n" + "=" * 60)
    print("STEP 2: Fetching Emails with Fixed Metadata")
    print("=" * 60)
    
    from app.config.settings import get_settings
    from app.ingest.imap_loader import fetch_emails
    
    settings = get_settings()
    
    print("\nFetching emails from server...")
    print("This may take a few minutes for large mailboxes...")
    
    # Fetch more emails for a complete index
    emails = fetch_emails(settings, limit=1000)  # Adjust limit as needed
    
    if not emails:
        print("[ERROR] No emails fetched. Please check your email settings.")
        return None
    
    print(f"\n[SUCCESS] Fetched {len(emails)} emails")
    
    # Verify metadata is present
    emails_with_metadata = 0
    emails_missing_metadata = []
    
    for i, email in enumerate(emails):
        has_from = bool(email.get('from') and str(email['from']).strip())
        has_subject = bool(email.get('subject') and str(email['subject']).strip())
        
        if has_from and has_subject:
            emails_with_metadata += 1
        else:
            emails_missing_metadata.append(i)
    
    print(f"\nMetadata Statistics:")
    print(f"  - Emails with complete metadata: {emails_with_metadata}/{len(emails)}")
    print(f"  - Success rate: {emails_with_metadata/len(emails)*100:.1f}%")
    
    if emails_missing_metadata[:5]:  # Show first 5 problematic emails
        print(f"\n[WARN] Sample emails missing metadata (indices): {emails_missing_metadata[:5]}")
    
    # Save emails to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"data/raw/emails_rebuilt_{timestamp}.json"
    
    os.makedirs("data/raw", exist_ok=True)
    
    print(f"\nSaving emails to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(emails, f, indent=2, ensure_ascii=False)
    
    print(f"[SUCCESS] Saved {len(emails)} emails")
    
    return output_file

def build_fresh_index(raw_file):
    """Build a completely fresh index with proper metadata"""
    print("\n" + "=" * 60)
    print("STEP 3: Building Fresh Index")
    print("=" * 60)
    
    from app.indexing.build_index import build_index
    
    print("\nBuilding index with the following features:")
    print("  - Smart chunking for better retrieval")
    print("  - Complete metadata (from, to, subject, date)")
    print("  - Quality scoring")
    print("  - Hybrid search capability")
    
    try:
        # Build the index
        print("\nProcessing emails and creating embeddings...")
        build_index(raw_file)
        print("\n[SUCCESS] Index built successfully!")
        return True
    except Exception as e:
        print(f"\n[ERROR] Failed to build index: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_index():
    """Verify the index has proper metadata"""
    print("\n" + "=" * 60)
    print("STEP 4: Verifying Index")
    print("=" * 60)
    
    try:
        # Test a simple query
        from app.qa.flexible_query_bridge import ask
        
        print("\nTesting index with sample query...")
        result = ask("Show me recent emails", include_sources=True)
        
        if result and result.get('citations'):
            print(f"\n[SUCCESS] Index is working! Found {len(result['citations'])} results")
            
            # Check if citations have metadata
            print("\nChecking metadata in results:")
            for i, citation in enumerate(result['citations'][:3], 1):
                from_field = citation.get('from', 'MISSING')
                subject = citation.get('subject', 'MISSING')
                
                # Handle tuple format
                if isinstance(from_field, tuple):
                    from_display = from_field[0] if from_field[0] else from_field[1]
                else:
                    from_display = str(from_field)[:50]
                
                print(f"\n  Email {i}:")
                print(f"    From: {from_display}")
                print(f"    Subject: {str(subject)[:50]}")
                
                # Check for metadata
                if from_field == 'MISSING' or not from_field:
                    print(f"    [WARN] Missing 'from' metadata")
                if subject == 'MISSING' or not subject:
                    print(f"    [WARN] Missing 'subject' metadata")
            
            return True
        else:
            print("[WARN] No results returned from query")
            return False
            
    except Exception as e:
        print(f"[ERROR] Verification failed: {e}")
        return False

def main():
    """Main rebuild process"""
    print("COMPLETE INDEX REBUILD WITH METADATA FIX")
    print("=" * 60)
    print("This will:")
    print("1. Clear the old index completely")
    print("2. Fetch all emails with proper metadata")
    print("3. Build a fresh index")
    print("4. Verify metadata is working")
    print("=" * 60)
    
    response = input("\nProceed with rebuild? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    # Step 1: Clear old index
    clear_old_index()
    
    # Step 2: Fetch emails with metadata
    raw_file = fetch_all_emails_with_metadata()
    if not raw_file:
        print("\n[ERROR] Failed to fetch emails. Please check your email configuration.")
        return
    
    # Step 3: Build fresh index
    success = build_fresh_index(raw_file)
    if not success:
        print("\n[ERROR] Failed to build index. Please check the errors above.")
        return
    
    # Step 4: Verify
    verified = verify_index()
    
    # Final summary
    print("\n" + "=" * 60)
    print("REBUILD COMPLETE!")
    print("=" * 60)
    
    if verified:
        print("\n[SUCCESS] Your email index has been rebuilt with proper metadata.")
        print("\nYou can now:")
        print("1. Run the UI: python run_ui.py")
        print("2. Ask questions about your emails")
        print("3. All emails should show proper from/subject information")
    else:
        print("\n[WARN] Index was rebuilt but verification showed some issues.")
        print("Please try running the UI and test with some queries.")
    
    print("\nTip: Use the 'Update Emails' button in the UI for future incremental updates.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()