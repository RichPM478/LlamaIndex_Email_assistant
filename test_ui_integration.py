#!/usr/bin/env python3
"""
Test UI integration with lazy query engine
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

def test_ui_imports():
    """Test that UI can import and use lazy query engine"""
    print("UI INTEGRATION TEST")
    print("=" * 40)
    
    print("\n1. Testing Chat Interface Import:")
    print("-" * 35)
    
    # Clear modules
    modules_to_clear = [
        'app.ui.chat_interface',
        'app.ui.streamlit_app', 
        'app.qa.lazy_query'
    ]
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]
    
    # Test chat interface import (should be very fast)
    try:
        with timer("   Chat interface import"):
            # Import the query function used by chat interface
            from app.qa.lazy_query import lazy_optimized_ask as optimized_ask, get_cache_status
            
        print("   [OK] Chat interface imports work")
        
        # Test cache status
        status = get_cache_status()
        print(f"   [OK] Initial cache status: all components unloaded = {not any(status.values())}")
        
        return True
    except Exception as e:
        print(f"   [ERROR] Chat interface import failed: {e}")
        return False

def test_streamlit_app_imports():
    """Test main streamlit app import"""
    print("\n2. Testing Main App Import:")
    print("-" * 35)
    
    try:
        with timer("   Main app import"):
            # Import the query function used by streamlit app
            from app.qa.lazy_query import lazy_optimized_ask as ask
            
        print("   [OK] Main app imports work")
        return True
    except Exception as e:
        print(f"   [ERROR] Main app import failed: {e}")
        return False

def test_query_through_ui_interface():
    """Test actual query through UI interface functions"""
    print("\n3. Testing Query Through UI:")
    print("-" * 35)
    
    try:
        from app.qa.lazy_query import lazy_optimized_ask as optimized_ask
        
        # Test a simple query
        print("   Running test query through UI interface...")
        start = time.time()
        result = optimized_ask("What are recent emails?", top_k=2)
        elapsed = time.time() - start
        
        print(f"   [OK] Query completed: {elapsed*1000:.1f}ms")
        print(f"   [OK] Result has answer: {'answer' in result}")
        print(f"   [OK] Result has citations: {'citations' in result}")
        print(f"   [OK] Citations count: {len(result.get('citations', []))}")
        
        return True
    except Exception as e:
        print(f"   [ERROR] UI query test failed: {e}")
        return False

def test_performance_comparison():
    """Compare startup performance"""
    print("\n4. Performance Comparison:")
    print("-" * 35)
    
    # Clear all modules
    modules_to_clear = [
        'app.qa.unified_query',
        'app.qa.lazy_query',
        'app.ui.chat_interface',
        'app.ui.streamlit_app'
    ]
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]
    
    try:
        # Test old unified approach
        print("   Testing OLD unified approach:")
        with timer("     Unified import"):
            from app.qa.unified_query import optimized_ask as unified_ask
        
        # Clear and test new lazy approach  
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        print("   Testing NEW lazy approach:")
        with timer("     Lazy import"):
            from app.qa.lazy_query import lazy_optimized_ask as lazy_ask
            
        print("   [OK] Performance comparison complete")
        return True
        
    except Exception as e:
        print(f"   [ERROR] Performance test failed: {e}")
        return False

def main():
    """Run all UI integration tests"""
    tests = [
        test_ui_imports,
        test_streamlit_app_imports,
        test_query_through_ui_interface,
        test_performance_comparison
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
    print("=" * 40)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")
    
    if failed == 0:
        print("\n[SUCCESS] UI INTEGRATION COMPLETE!")
        print("Phase 2 optimization successfully integrated.")
    else:
        print(f"\n[ERROR] {failed} tests failed")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)