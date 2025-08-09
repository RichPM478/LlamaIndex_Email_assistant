#!/usr/bin/env python3
"""
Test Query Intelligence - Phase 3C
Demonstrate enhanced query understanding and processing
"""

import os
import sys

# Add project root to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

def test_query_intelligence():
    """Test the query intelligence system"""
    print("PHASE 3C: QUERY INTELLIGENCE TEST")
    print("=" * 50)
    
    from app.intelligence.query_intelligence import query_intelligence
    
    # Test queries with different intents
    test_queries = [
        "emails from Mount Carmel about school trip",
        "what do I need to pay this month?", 
        "urgent emails from last week",
        "summarize recent project updates",
        "what tasks do I need to complete?",
        "any important notifications today?",
        "meeting emails with John Smith",
        "bills and invoices due soon",
    ]
    
    print("\n🧠 TESTING QUERY INTELLIGENCE:")
    print("-" * 50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Testing: \"{query}\"")
        print("-" * 40)
        
        # Analyze query
        enhancement = query_intelligence.analyze_query(query)
        
        # Show results
        print(f"   Intent: {enhancement.intent.value} ({enhancement.confidence:.1%})")
        print(f"   Enhanced: \"{enhancement.enhanced_query}\"")
        
        if enhancement.extracted_entities:
            entities = []
            for entity_type, values in enhancement.extracted_entities.items():
                if values:
                    entities.append(f"{entity_type}: {', '.join(map(str, values))}")
            if entities:
                print(f"   Entities: {' | '.join(entities)}")
        
        if enhancement.metadata_filters:
            filters = []
            for key, value in enhancement.metadata_filters.items():
                filters.append(f"{key}={value}")
            print(f"   Filters: {', '.join(filters)}")
        
        if enhancement.context_expansion:
            print(f"   Context: {enhancement.context_expansion}")
        
        print(f"   Suggested results: {enhancement.suggested_top_k}")

def test_intelligent_query_engine():
    """Test the intelligent query engine with real data"""
    print("\n\n🔍 TESTING INTELLIGENT QUERY ENGINE:")
    print("=" * 50)
    
    try:
        from app.qa.intelligent_query import intelligent_ask
        
        # Test with a sample query
        test_query = "urgent emails from Mount Carmel"
        print(f"\n🎯 Query: \"{test_query}\"")
        print("-" * 30)
        
        # Run intelligent query with debug
        result = intelligent_ask(test_query, top_k=3, debug=True)
        
        print(f"\n📊 Results: {len(result.get('citations', []))} emails found")
        print(f"⏱️  Response time: {result.get('response_time', 0):.2f}s")
        
        # Show intelligence metadata
        intelligence = result.get('query_intelligence', {})
        if intelligence:
            print(f"\n🧠 Intelligence Analysis:")
            print(f"   Intent: {intelligence.get('intent', 'unknown')}")
            print(f"   Confidence: {intelligence.get('confidence', 0):.1%}")
            print(f"   Processing time: {intelligence.get('processing_time', 0):.3f}s")
        
        # Show sample results
        citations = result.get('citations', [])
        if citations:
            print(f"\n📧 Sample Results:")
            for i, citation in enumerate(citations[:2], 1):
                sender = citation.get('from', 'Unknown')[:30]
                subject = citation.get('subject', 'No subject')[:40]
                print(f"   {i}. {sender} - {subject}")
                
                # Show intelligence enhancements
                if citation.get('urgency_indicators'):
                    print(f"      🚨 Urgency: {', '.join(citation['urgency_indicators'])}")
                if citation.get('highlighted_entities'):
                    entities = [f"{e['type']}:{e['value']}" for e in citation['highlighted_entities']]
                    print(f"      🔍 Entities: {', '.join(entities)}")
        
    except Exception as e:
        print(f"❌ Error testing intelligent query: {e}")
        print("Note: This requires the email index to be built first")

def show_intelligence_capabilities():
    """Show the capabilities of the query intelligence system"""
    print("\n\n✨ QUERY INTELLIGENCE CAPABILITIES:")
    print("=" * 50)
    
    capabilities = [
        "🎯 Intent Recognition - Understands what you're looking for",
        "🔍 Entity Extraction - Finds names, dates, amounts automatically",
        "📝 Query Enhancement - Adds relevant search terms",
        "🎛️ Smart Filtering - Applies metadata filters based on context",
        "🌐 Context Expansion - Understands domain-specific language",
        "⚡ Optimized Retrieval - Suggests best number of results",
        "🧠 Semantic Understanding - Goes beyond keyword matching",
        "📊 Result Ranking - Prioritizes most relevant emails",
    ]
    
    for capability in capabilities:
        print(f"  {capability}")
    
    print(f"\n📋 Supported Query Types:")
    intents = [
        "Search by sender: 'emails from John'",
        "Search by timeframe: 'last week's emails'", 
        "Search urgent items: 'important emails'",
        "Search categories: 'payment emails'",
        "Ask for summary: 'what's new?'",
        "Ask for actions: 'what do I need to do?'",
        "Search topics: 'project updates'",
        "General search: 'meeting tomorrow'",
    ]
    
    for intent in intents:
        print(f"  • {intent}")

def main():
    """Run all query intelligence tests"""
    test_query_intelligence()
    test_intelligent_query_engine() 
    show_intelligence_capabilities()
    
    print(f"\n🎉 PHASE 3C QUERY INTELLIGENCE - COMPLETE!")
    print(f"Your email assistant now understands queries much better!")

if __name__ == "__main__":
    main()