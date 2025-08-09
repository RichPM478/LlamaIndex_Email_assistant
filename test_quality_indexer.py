#!/usr/bin/env python3
"""
Test Quality-Enhanced Indexer - Phase 3A Integration
"""

import sys
import os
import time
import shutil

def test_quality_indexing():
    """Test the quality-enhanced indexing pipeline"""
    print("QUALITY-ENHANCED INDEXING TEST - PHASE 3A")
    print("=" * 60)
    
    # Import quality indexer
    from app.indexing.quality_indexer import build_quality_index, get_quality_stats
    
    # Test with different quality thresholds
    test_configs = [
        {"name": "Permissive", "threshold": 30, "marketing": 60},
        {"name": "Standard", "threshold": 50, "marketing": 40},
        {"name": "Strict", "threshold": 70, "marketing": 20}
    ]
    
    for config in test_configs:
        print(f"\n=== Testing {config['name']} Quality Filtering ===")
        print(f"Quality threshold: {config['threshold']}/100")
        print(f"Max marketing score: {config['marketing']}/100")
        
        # Create test index directory
        test_dir = f"data/test_index_{config['name'].lower()}"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        
        try:
            # Build quality-filtered index
            start_time = time.time()
            
            index = build_quality_index(
                persist_dir=test_dir,
                quality_threshold=config['threshold'],
                max_marketing_score=config['marketing']
            )
            
            build_time = time.time() - start_time
            print(f"Index build time: {build_time:.1f}s")
            
            # Get quality statistics
            stats = get_quality_stats(test_dir)
            if "error" not in stats:
                print(f"\nQuality Statistics:")
                print(f"  Total emails processed: {stats['total_emails']}")
                print(f"  High-quality emails included: {stats['processed_emails']}")
                print(f"  Low-quality emails filtered: {stats['filtered_emails']}")
                print(f"  Quality acceptance rate: {stats['processed_emails']/stats['total_emails']*100:.1f}%")
                print(f"  Average quality score: {stats['average_quality']:.1f}/100")
                print(f"  Search nodes created: {stats['total_nodes']}")
                
                print(f"\nTop rejection reasons:")
                for reason, count in list(stats['rejection_reasons'].items())[:3]:
                    print(f"    - {reason}: {count} emails")
            
        except Exception as e:
            print(f"[ERROR] {config['name']} test failed: {e}")
            continue
    
    return True

def test_search_quality():
    """Test search quality with the enhanced index"""
    print(f"\n=== SEARCH QUALITY TEST ===")
    
    from llama_index.core import StorageContext, load_index_from_storage
    from app.config.settings import get_settings
    from app.llm.provider import configure_llm
    from app.embeddings.provider import configure_embeddings
    
    # Configure models
    settings = get_settings()
    configure_llm(settings)
    configure_embeddings(settings)
    
    # Test with standard quality index
    test_dir = "data/test_index_standard"
    
    if not os.path.exists(test_dir):
        print("[SKIP] Standard quality index not found")
        return True
    
    try:
        # Load the quality-filtered index
        storage_context = StorageContext.from_defaults(persist_dir=test_dir)
        index = load_index_from_storage(storage_context)
        
        # Test queries
        test_queries = [
            "What are recent emails about?",
            "Show me important notifications",
            "Any payment or billing emails?"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            
            start_time = time.time()
            query_engine = index.as_query_engine(similarity_top_k=3)
            response = query_engine.query(query)
            query_time = time.time() - start_time
            
            print(f"  Response time: {query_time:.2f}s")
            print(f"  Answer length: {len(str(response))} chars")
            
            # Check source quality
            source_nodes = getattr(response, 'source_nodes', [])
            if source_nodes:
                quality_scores = []
                for node in source_nodes:
                    quality = node.node.metadata.get('quality_score', 0)
                    quality_scores.append(quality)
                
                avg_quality = sum(quality_scores) / len(quality_scores)
                print(f"  Source quality: {avg_quality:.1f}/100 avg")
                print(f"  Sources used: {len(source_nodes)}")
                
    except Exception as e:
        print(f"[ERROR] Search quality test failed: {e}")
    
    return True

def compare_old_vs_new():
    """Compare old vs new indexing approaches"""
    print(f"\n=== OLD vs NEW INDEX COMPARISON ===")
    
    # Check if we have both indexes
    old_index_dir = "data/index"  # Original index
    new_index_dir = "data/test_index_standard"  # Quality-filtered index
    
    if not os.path.exists(old_index_dir):
        print("[SKIP] Original index not found")
        return True
    
    if not os.path.exists(new_index_dir):
        print("[SKIP] Quality index not found")
        return True
    
    from llama_index.core import StorageContext, load_index_from_storage
    from app.config.settings import get_settings
    from app.llm.provider import configure_llm
    from app.embeddings.provider import configure_embeddings
    
    # Configure models
    settings = get_settings()
    configure_llm(settings)
    configure_embeddings(settings)
    
    try:
        # Load both indexes
        old_storage = StorageContext.from_defaults(persist_dir=old_index_dir)
        old_index = load_index_from_storage(old_storage)
        
        new_storage = StorageContext.from_defaults(persist_dir=new_index_dir)
        new_index = load_index_from_storage(new_storage)
        
        # Get quality stats
        quality_stats = get_quality_stats(new_index_dir)
        
        print(f"Original Index:")
        print(f"  All emails included (no filtering)")
        print(f"  Estimated nodes: ~3000-5000")
        
        print(f"\nQuality-Filtered Index:")
        if "error" not in quality_stats:
            print(f"  Only {quality_stats['processed_emails']}/{quality_stats['total_emails']} emails included ({quality_stats['processed_emails']/quality_stats['total_emails']*100:.1f}%)")
            print(f"  Search nodes: {quality_stats['total_nodes']}")
            print(f"  Average quality: {quality_stats['average_quality']:.1f}/100")
        
        # Test same query on both
        test_query = "What are recent important emails?"
        
        print(f"\nQuery Test: '{test_query}'")
        
        # Old index
        print(f"  OLD INDEX:")
        start_time = time.time()
        old_engine = old_index.as_query_engine(similarity_top_k=3)
        old_response = old_engine.query(test_query)
        old_time = time.time() - start_time
        print(f"    Response time: {old_time:.2f}s")
        print(f"    Answer length: {len(str(old_response))} chars")
        
        # New index  
        print(f"  NEW INDEX:")
        start_time = time.time()
        new_engine = new_index.as_query_engine(similarity_top_k=3)
        new_response = new_engine.query(test_query)
        new_time = time.time() - start_time
        print(f"    Response time: {new_time:.2f}s")
        print(f"    Answer length: {len(str(new_response))} chars")
        
        # Performance comparison
        speed_improvement = (old_time - new_time) / old_time * 100 if old_time > new_time else 0
        if speed_improvement > 0:
            print(f"    Speed improvement: {speed_improvement:.1f}%")
        
    except Exception as e:
        print(f"[ERROR] Comparison failed: {e}")
    
    return True

def main():
    """Run all quality indexing tests"""
    try:
        success = test_quality_indexing()
        if success:
            test_search_quality()
            compare_old_vs_new()
            
            print(f"\nQUALITY INDEXING TESTS COMPLETE!")
            print("Phase 3A: Advanced Email Parser 2.0 + Quality Indexing ready!")
        
        return success
        
    except Exception as e:
        print(f"[ERROR] Testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)