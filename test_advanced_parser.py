#!/usr/bin/env python3
"""
Test Advanced Email Parser 2.0 - Phase 3A Data Pipeline
Compare content quality improvements vs current parser
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any

def test_parser_comparison():
    """Compare old vs new parser on real email data"""
    print("ADVANCED EMAIL PARSER 2.0 - QUALITY BENCHMARK")
    print("=" * 70)
    
    # Load real email data
    data_file = "data/raw/emails_20250809_001105.json"
    
    if not Path(data_file).exists():
        print(f"[ERROR] Data file not found: {data_file}")
        return False
    
    with open(data_file, 'r', encoding='utf-8') as f:
        emails = json.load(f)
    
    print(f"[INFO] Testing with {len(emails)} real emails")
    
    # Import parsers
    from app.ingest.email_parser import CleanEmailParser
    from app.ingest.advanced_email_parser import AdvancedEmailParser
    
    old_parser = CleanEmailParser()
    new_parser = AdvancedEmailParser()
    
    # Test sample of emails for detailed comparison
    sample_emails = emails[:10]  # Test first 10 emails
    
    print(f"\nDETAILED COMPARISON (First {len(sample_emails)} emails)")
    print("=" * 70)
    
    total_old_length = 0
    total_new_length = 0
    quality_scores = []
    high_quality_count = 0
    
    for i, email in enumerate(sample_emails, 1):
        print(f"\n--- EMAIL {i}: {email.get('subject', 'No subject')[:50]}... ---")
        
        # Old parser
        old_start = time.time()
        old_body = old_parser.clean_email_body(email.get('body', ''), 'text/html')
        old_time = time.time() - old_start
        
        # New parser  
        new_start = time.time()
        parsed_result = new_parser.parse_email_advanced(email)
        new_time = time.time() - new_start
        
        # Extract results
        new_body = parsed_result['clean_body']
        quality = parsed_result['quality_score']
        quality_scores.append(quality)
        
        # Track lengths
        total_old_length += len(old_body)
        total_new_length += len(new_body)
        
        # Quality classification
        if quality >= 60:
            high_quality_count += 1
            quality_label = "HIGH"
        elif quality >= 30:
            quality_label = "MEDIUM"
        else:
            quality_label = "LOW"
        
        print(f"  Sender: {parsed_result['clean_sender']}")
        print(f"  Quality Score: {quality:.1f}/100 ({quality_label})")
        print(f"  Content Ratio: {parsed_result['content_ratio']:.1%}")
        print(f"  Marketing Score: {parsed_result['marketing_score']:.1f}/100")
        print(f"  Template Score: {parsed_result['template_score']:.1f}/100")
        print(f"  Language Confidence: {parsed_result['language_confidence']:.1f}%")
        
        # Length comparison
        old_len = len(old_body)
        new_len = len(new_body)
        reduction = (old_len - new_len) / max(1, old_len) * 100
        print(f"  Length: {old_len} -> {new_len} chars ({reduction:+.1f}% change)")
        
        # Processing time
        print(f"  Processing: {old_time*1000:.1f}ms -> {new_time*1000:.1f}ms")
        
        # Quality issues
        if parsed_result['quality_issues']:
            print(f"  Issues: {', '.join(parsed_result['quality_issues'][:3])}")
        
        # Show content preview
        preview_old = old_body[:150].replace('\n', ' ')
        preview_new = new_body[:150].replace('\n', ' ')
        
        if preview_old != preview_new:
            print(f"  OLD: {preview_old}...")
            print(f"  NEW: {preview_new}...")
    
    # Overall statistics
    print(f"\nOVERALL STATISTICS")
    print("=" * 70)
    
    avg_quality = sum(quality_scores) / len(quality_scores)
    print(f"Average Quality Score: {avg_quality:.1f}/100")
    print(f"High Quality Emails: {high_quality_count}/{len(sample_emails)} ({high_quality_count/len(sample_emails)*100:.1f}%)")
    
    avg_old_length = total_old_length / len(sample_emails)
    avg_new_length = total_new_length / len(sample_emails)
    overall_reduction = (total_old_length - total_new_length) / max(1, total_old_length) * 100
    
    print(f"Average Content Length: {avg_old_length:.0f} → {avg_new_length:.0f} chars")
    print(f"Overall Size Reduction: {overall_reduction:.1f}%")
    
    return True

def test_quality_filtering():
    """Test quality-based filtering"""
    print(f"\nQUALITY FILTERING TEST")
    print("=" * 70)
    
    # Load emails
    data_file = "data/raw/emails_20250809_001105.json"
    with open(data_file, 'r', encoding='utf-8') as f:
        emails = json.load(f)
    
    from app.ingest.advanced_email_parser import AdvancedEmailParser
    parser = AdvancedEmailParser()
    
    quality_thresholds = [40, 60, 80]
    
    for threshold in quality_thresholds:
        print(f"\n--- Quality Threshold: {threshold}/100 ---")
        
        high_quality_emails = []
        total_processed = 0
        
        for email in emails:
            result = parser.parse_email_advanced(email)
            total_processed += 1
            
            if result['quality_score'] >= threshold:
                high_quality_emails.append({
                    'subject': result['clean_subject'],
                    'sender': result['clean_sender'],
                    'quality': result['quality_score'],
                    'length': len(result['clean_body'])
                })
        
        print(f"  Emails meeting threshold: {len(high_quality_emails)}/{total_processed} ({len(high_quality_emails)/total_processed*100:.1f}%)")
        
        if high_quality_emails:
            # Show top quality emails
            high_quality_emails.sort(key=lambda x: x['quality'], reverse=True)
            print(f"  Top quality emails:")
            for email in high_quality_emails[:3]:
                print(f"    - {email['quality']:.1f}: {email['subject'][:40]}... (from {email['sender']})")

def test_specific_noise_patterns():
    """Test removal of specific noise patterns"""
    print(f"\nNOISE PATTERN REMOVAL TEST")  
    print("=" * 70)
    
    from app.ingest.advanced_email_parser import AdvancedEmailParser
    parser = AdvancedEmailParser()
    
    # Test cases for specific noise patterns
    test_cases = [
        {
            'name': 'HTML Entity Spam',
            'input': 'Important message &zwnj; &#847; &#8199; &zwnj; &#847; &#8199; &zwnj; &#847; &#8199; please read this.',
            'expected_improvement': 'Reduced HTML entity noise'
        },
        {
            'name': 'Marketing Spam',
            'input': 'SHOP NOW! LIMITED TIME OFFER! BUY NOW and save 50% OFF! EXCLUSIVE DEAL ENDS TODAY!',
            'expected_improvement': 'Marketing content removal'
        },
        {
            'name': 'Tracking URLs',
            'input': 'Click here: https://example.com/page?utm_source=email&utm_campaign=test&_ri_=X0Gzc2X%3DAQjkPkSUTQGvR3f2CnSgzf7hN3HF9GKPOqY86yzcpC6U0muvhyNFKzaijJ5b47yiM7zezfJHJfAkOR2zf',
            'expected_improvement': 'URL cleanup'
        },
        {
            'name': 'Email Signature',
            'input': 'Thanks for your email. Best regards, John Smith. This email was sent to you because you subscribed. Unsubscribe here. © 2025 Company Inc. All rights reserved.',
            'expected_improvement': 'Signature removal'
        }
    ]
    
    for test_case in test_cases:
        print(f"\n--- Testing: {test_case['name']} ---")
        print(f"  Input ({len(test_case['input'])} chars): {test_case['input'][:100]}...")
        
        # Create test email
        test_email = {
            'subject': 'Test Email',
            'from': 'test@example.com',
            'body': test_case['input']
        }
        
        result = parser.parse_email_advanced(test_email)
        clean_output = result['clean_body']
        
        print(f"  Output ({len(clean_output)} chars): {clean_output[:100]}...")
        print(f"  Quality Score: {result['quality_score']:.1f}/100")
        print(f"  Noise Reduction: {(len(test_case['input']) - len(clean_output)) / len(test_case['input']) * 100:.1f}%")
        print(f"  Expected: {test_case['expected_improvement']}")

def main():
    """Run all advanced parser tests"""
    try:
        success = test_parser_comparison()
        if success:
            test_quality_filtering()
            test_specific_noise_patterns()
            
            print(f"\nADVANCED PARSER TESTING COMPLETE!")
            print("Phase 3A: Advanced Email Parser 2.0 ready for integration.")
        
        return success
        
    except Exception as e:
        print(f"[ERROR] Testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)