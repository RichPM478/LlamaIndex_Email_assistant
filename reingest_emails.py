"""
Re-ingest emails with proper metadata extraction
This script will fetch emails again and save them with correct metadata
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Set encoding for Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, str(Path(__file__).parent))

def reingest_emails(limit=500):
    """Re-ingest emails with fixed metadata extraction"""
    from app.config.settings import get_settings
    from app.ingest.imap_loader import fetch_emails
    
    print("="*60)
    print("EMAIL RE-INGESTION WITH METADATA FIX")
    print("="*60)
    
    settings = get_settings()
    
    # Fetch emails with fixed loader
    print(f"\nFetching up to {limit} emails...")
    emails = fetch_emails(settings, limit=limit)
    
    if not emails:
        print("[ERROR] No emails fetched")
        return False
    
    print(f"[SUCCESS] Fetched {len(emails)} emails")
    
    # Verify metadata is present
    emails_with_metadata = 0
    sample_emails = []
    
    for i, email in enumerate(emails):
        has_from = bool(email.get('from') and str(email['from']).strip())
        has_subject = bool(email.get('subject') and str(email['subject']).strip())
        
        if has_from and has_subject:
            emails_with_metadata += 1
            
        # Collect samples for display
        if i < 5:
            sample_emails.append({
                'from': str(email.get('from', ''))[:50],
                'subject': str(email.get('subject', ''))[:50],
                'has_metadata': has_from and has_subject
            })
    
    # Display sample emails
    print("\nSample emails:")
    for i, sample in enumerate(sample_emails, 1):
        status = "[OK]" if sample['has_metadata'] else "[NO METADATA]"
        print(f"{i}. {status}")
        print(f"   From: {sample['from']}")
        print(f"   Subject: {sample['subject']}")
    
    print(f"\nMetadata Statistics:")
    print(f"  Emails with metadata: {emails_with_metadata}/{len(emails)}")
    print(f"  Success rate: {emails_with_metadata/len(emails)*100:.1f}%")
    
    if emails_with_metadata < len(emails) * 0.9:  # Less than 90% have metadata
        print("\n[WARNING] Many emails missing metadata!")
        response = input("Continue saving? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return False
    
    # Save to new file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"data/raw/emails_fixed_{timestamp}.json"
    
    # Ensure directory exists
    os.makedirs("data/raw", exist_ok=True)
    
    # Save emails
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(emails, f, indent=2, ensure_ascii=False)
    
    print(f"[SUCCESS] Saved {len(emails)} emails to {output_file}")
    
    # Now rebuild the index with the new data
    print("\n" + "="*60)
    print("REBUILDING INDEX WITH FIXED METADATA")
    print("="*60)
    
    response = input("\nRebuild index now? (y/n): ")
    if response.lower() == 'y':
        from app.indexing.build_index import build_email_index
        
        print("\nBuilding index...")
        try:
            build_email_index(output_file)
            print("[SUCCESS] Index rebuilt with proper metadata!")
        except Exception as e:
            print(f"[ERROR] Failed to rebuild index: {e}")
            return False
    
    return True

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Re-ingest emails with metadata fix")
    parser.add_argument('--limit', type=int, default=500, help='Number of emails to fetch (default: 500)')
    args = parser.parse_args()
    
    success = reingest_emails(limit=args.limit)
    
    if success:
        print("\n" + "="*60)
        print("RE-INGESTION COMPLETE!")
        print("Your emails now have proper metadata.")
        print("You can run the UI with: python run_ui.py")
        print("="*60)
    else:
        print("\n[ERROR] Re-ingestion failed. Please check the errors above.")

if __name__ == "__main__":
    main()