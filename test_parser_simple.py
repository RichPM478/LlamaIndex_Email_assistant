#!/usr/bin/env python3
"""
Simple test for Advanced Email Parser 2.0 - Phase 3A Data Pipeline
Focus on quality metrics without unicode issues
"""

import json
import time
from pathlib import Path

def test_quality_improvements():
    """Test quality improvements with the new parser"""
    print("ADVANCED EMAIL PARSER 2.0 - QUALITY ASSESSMENT")
    print("=" * 60)
    
    # Load email data
    data_file = "data/raw/emails_20250809_001105.json"
    
    if not Path(data_file).exists():
        print(f"[ERROR] Data file not found: {data_file}")
        return False
    
    with open(data_file, 'r', encoding='utf-8') as f:
        emails = json.load(f)
    
    print(f"[INFO] Testing with {len(emails)} emails")
    
    # Import new parser
    from app.ingest.advanced_email_parser import AdvancedEmailParser
    parser = AdvancedEmailParser()
    
    # Process sample of emails
    sample_size = 20
    sample_emails = emails[:sample_size]
    
    print(f"\n=== PROCESSING {sample_size} SAMPLE EMAILS ===")
    
    results = []
    processing_times = []
    
    for i, email in enumerate(sample_emails, 1):
        print(f"\nEmail {i}: {email.get('subject', 'No subject')[:50]}...")
        
        start_time = time.time()
        result = parser.parse_email_advanced(email)
        processing_time = time.time() - start_time
        processing_times.append(processing_time)
        
        # Extract key metrics
        quality_score = result['quality_score']
        content_ratio = result['content_ratio']
        marketing_score = result['marketing_score']
        template_score = result['template_score']
        language_confidence = result['language_confidence']
        
        original_length = len(email.get('body', ''))
        clean_length = len(result['clean_body'])
        size_change = (clean_length - original_length) / max(1, original_length) * 100
        
        print(f"  Quality Score: {quality_score:.1f}/100")
        print(f"  Content Ratio: {content_ratio:.1%}")
        print(f"  Marketing Score: {marketing_score:.1f}")
        print(f"  Language Confidence: {language_confidence:.1f}%")
        print(f"  Size Change: {size_change:+.1f}%")
        print(f"  Processing Time: {processing_time*1000:.1f}ms")
        
        if result['quality_issues']:
            print(f"  Issues: {len(result['quality_issues'])} detected")
        
        results.append({
            'quality': quality_score,
            'content_ratio': content_ratio,
            'marketing': marketing_score,
            'template': template_score,
            'language': language_confidence,
            'size_change': size_change,
            'processing_time': processing_time,
            'issues': len(result['quality_issues'])
        })
    
    # Calculate statistics
    print(f"\n=== OVERALL STATISTICS ===")
    
    avg_quality = sum(r['quality'] for r in results) / len(results)
    avg_content_ratio = sum(r['content_ratio'] for r in results) / len(results)
    avg_marketing = sum(r['marketing'] for r in results) / len(results)
    avg_language = sum(r['language'] for r in results) / len(results)
    avg_processing = sum(processing_times) / len(processing_times)
    
    high_quality_count = sum(1 for r in results if r['quality'] >= 60)
    low_marketing_count = sum(1 for r in results if r['marketing'] < 30)
    
    print(f"Average Quality Score: {avg_quality:.1f}/100")
    print(f"Average Content Ratio: {avg_content_ratio:.1%}")
    print(f"Average Marketing Score: {avg_marketing:.1f}/100")
    print(f"Average Language Confidence: {avg_language:.1f}%")
    print(f"Average Processing Time: {avg_processing*1000:.1f}ms")
    
    print(f"\nQuality Distribution:")
    print(f"  High Quality (60+): {high_quality_count}/{len(results)} ({high_quality_count/len(results)*100:.1f}%)")
    print(f"  Low Marketing (<30): {low_marketing_count}/{len(results)} ({low_marketing_count/len(results)*100:.1f}%)")
    
    # Quality filtering test
    print(f"\n=== QUALITY FILTERING TEST ===")
    
    thresholds = [40, 60, 80]
    for threshold in thresholds:
        passing_count = sum(1 for r in results if r['quality'] >= threshold)
        print(f"Emails passing {threshold}+ quality: {passing_count}/{len(results)} ({passing_count/len(results)*100:.1f}%)")
    
    return True

def test_noise_removal():
    """Test specific noise removal capabilities"""
    print(f"\n=== NOISE REMOVAL TEST ===")
    
    from app.ingest.advanced_email_parser import AdvancedEmailParser
    parser = AdvancedEmailParser()
    
    # Test cases
    test_cases = [
        {
            'name': 'Clean Business Email',
            'body': 'Hi John, Thank you for your inquiry about our services. I would be happy to schedule a meeting to discuss your requirements. Best regards, Sarah'
        },
        {
            'name': 'Marketing Heavy Email',  
            'body': 'SHOP NOW! LIMITED TIME OFFER! Save 50% OFF everything! BUY NOW before this EXCLUSIVE DEAL ends! Click here to SHOP NOW!'
        },
        {
            'name': 'HTML Entity Spam',
            'body': 'Important message &zwnj; &#847; &#8199; &zwnj; &#847; &#8199; with some actual content here.'
        },
        {
            'name': 'Template Email',
            'body': 'Your job alert for Senior Developer. New jobs match your preferences: Senior Developer at Company A, Senior Developer at Company B.'
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        
        test_email = {
            'subject': test_case['name'],
            'from': 'test@example.com', 
            'body': test_case['body']
        }
        
        result = parser.parse_email_advanced(test_email)
        
        print(f"  Original Length: {len(test_case['body'])}")
        print(f"  Clean Length: {len(result['clean_body'])}")
        print(f"  Quality Score: {result['quality_score']:.1f}")
        print(f"  Marketing Score: {result['marketing_score']:.1f}")
        print(f"  Content Ratio: {result['content_ratio']:.1%}")

def main():
    """Run parser quality tests"""
    try:
        success = test_quality_improvements()
        if success:
            test_noise_removal()
            print(f"\nADVANCED PARSER TESTING COMPLETE!")
            print("Ready to integrate Advanced Email Parser 2.0!")
        
        return success
        
    except Exception as e:
        print(f"[ERROR] Testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)