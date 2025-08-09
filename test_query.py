#!/usr/bin/env python3
"""Test the optimized query system"""

from app.qa.optimized_query import optimized_ask
import time

def clean_text(text):
    """Clean text for safe printing"""
    # Remove zero-width characters and other problematic unicode
    import re
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
    # Replace other non-ASCII with space
    text = ''.join(c if ord(c) < 128 else ' ' for c in text)
    return text.strip()

def test_queries():
    print("Testing Email Query System")
    print("=" * 60)
    
    test_cases = [
        "What was my latest email about?",
        "Show me emails about payments or bills",
        "Any emails from LinkedIn?",
        "What events are coming up?",
    ]
    
    for query in test_cases:
        print(f"\nQuery: {query}")
        print("-" * 40)
        
        start = time.time()
        result = optimized_ask(query, top_k=3)
        elapsed = time.time() - start
        
        # Clean and truncate answer
        answer = clean_text(result["answer"])
        if len(answer) > 300:
            answer = answer[:300] + "..."
        
        print(f"Response Time: {elapsed:.2f} seconds")
        print(f"Answer: {answer}\n")
        
        if result.get("citations"):
            print("Top Sources:")
            for i, citation in enumerate(result["citations"][:3], 1):
                sender = clean_text(citation.get("from", "Unknown"))
                subject = clean_text(citation.get("subject", "No subject"))
                snippet = clean_text(citation.get("snippet", ""))[:100]
                
                print(f"  {i}. From: {sender}")
                print(f"     Subject: {subject}")
                if snippet:
                    print(f"     Preview: {snippet}...")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    test_queries()