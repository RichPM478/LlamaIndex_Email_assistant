#!/usr/bin/env python3
"""
Test the lazy query engine performance improvements.
"""
import time
import sys
from contextlib import contextmanager

@contextmanager
def timer(description):
    start = time.time()
    yield
    end = time.time()
    print(f"{description}: {(end - start) * 1000:.1f}ms")

def test_import_performance():
    """Test import performance of lazy vs unified query engines"""
    print("LAZY QUERY ENGINE PERFORMANCE TEST")
    print("=" * 50)
    
    print("\n1. UNIFIED ENGINE IMPORT (baseline):")
    print("-" * 40)
    
    # Clear modules first
    modules_to_clear = [
        'app.qa.unified_query',
        'app.qa.lazy_query',
    ]
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]
    
    # Test unified import (current implementation)
    with timer("   Unified engine import"):
        from app.qa.unified_query import optimized_ask as unified_ask
    
    print("\n2. LAZY ENGINE IMPORT (optimized):")
    print("-" * 40)
    
    # Clear and test lazy import
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]
    
    with timer("   Lazy engine import"):
        from app.qa.lazy_query import lazy_optimized_ask
    
    print("\n3. LAZY ENGINE FIRST QUERY (heavy loading):")
    print("-" * 40)
    
    # Test actual query performance
    test_query = "What are my recent emails?"
    
    print("   Running first query (triggers lazy loading)...")
    start = time.time()
    try:
        result = lazy_optimized_ask(test_query, top_k=3)
        elapsed = time.time() - start
        print(f"   [OK] First query completed: {elapsed*1000:.1f}ms")
        print(f"   [OK] Answer preview: {result['answer'][:100]}...")
        
        # Test second query (should be faster)
        print("\n   Running second query (using cached components)...")
        start = time.time()
        result2 = lazy_optimized_ask("Show me notifications", top_k=3)
        elapsed2 = time.time() - start
        print(f"   [OK] Second query completed: {elapsed2*1000:.1f}ms")
        print(f"   [OK] Performance gain: {((elapsed - elapsed2) / elapsed * 100):.1f}%")
        
        return True
        
    except Exception as e:
        print(f"   [ERROR] Query failed: {e}")
        return False

def test_cache_status():
    """Test lazy loading cache status"""
    print("\n4. CACHE STATUS MONITORING:")
    print("-" * 40)
    
    try:
        from app.qa.lazy_query import get_cache_status, clear_cache
        
        # Check status after queries
        status = get_cache_status()
        print(f"   [OK] Cache status: {status}")
        
        # Clear cache
        clear_cache()
        status_cleared = get_cache_status()
        print(f"   [OK] After clear: {status_cleared}")
        
        return True
        
    except Exception as e:
        print(f"   [ERROR] Cache status test failed: {e}")
        return False

def test_drop_in_compatibility():
    """Test that lazy engine is compatible with existing calls"""
    print("\n5. DROP-IN COMPATIBILITY TEST:")
    print("-" * 40)
    
    try:
        from app.qa.lazy_query import optimized_ask, simple_ask, advanced_ask
        
        # Test that all functions exist and are callable
        functions = [
            (optimized_ask, "optimized_ask"),
            (simple_ask, "simple_ask"), 
            (advanced_ask, "advanced_ask")
        ]
        
        for func, name in functions:
            if callable(func):
                print(f"   [OK] {name}: Available and callable")
            else:
                print(f"   [ERROR] {name}: Not callable")
                return False
        
        return True
        
    except Exception as e:
        print(f"   [ERROR] Compatibility test failed: {e}")
        return False

def profile_memory_usage():
    """Profile memory usage of lazy vs unified approaches"""
    print("\n6. MEMORY USAGE COMPARISON:")
    print("-" * 40)
    
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Memory before imports
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        print(f"   Memory before imports: {mem_before:.1f} MB")
        
        # Import lazy engine
        from app.qa.lazy_query import get_engine
        mem_after_import = process.memory_info().rss / 1024 / 1024
        print(f"   Memory after lazy import: {mem_after_import:.1f} MB")
        print(f"   Import overhead: {mem_after_import - mem_before:.1f} MB")
        
        # Run a query (triggers actual loading)
        engine = get_engine()
        result = engine.query("test query", top_k=2)
        mem_after_query = process.memory_info().rss / 1024 / 1024
        print(f"   Memory after first query: {mem_after_query:.1f} MB")
        print(f"   Query loading overhead: {mem_after_query - mem_after_import:.1f} MB")
        
        return True
        
    except ImportError:
        print("   [WARN] psutil not available, skipping memory test")
        return True
    except Exception as e:
        print(f"   [ERROR] Memory test failed: {e}")
        return False

def main():
    """Run all lazy query tests"""
    tests = [
        test_import_performance,
        test_cache_status,
        test_drop_in_compatibility,
        profile_memory_usage
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   [ERROR] Test failed with exception: {e}")
            failed += 1
    
    print(f"\nTEST RESULTS")
    print("=" * 50)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")
    
    if failed == 0:
        print("\n[SUCCESS] ALL LAZY QUERY TESTS PASSED!")
        print("Ready to integrate into UI for Phase 2 completion.")
    else:
        print(f"\n[ERROR] {failed} tests failed - needs attention")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)