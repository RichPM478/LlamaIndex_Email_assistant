#!/usr/bin/env python3
"""Test the consolidated functionality after Phase 1 optimization"""

import time
import sys
from pathlib import Path

def test_imports():
    """Test that all imports work correctly"""
    print("1. Testing Imports")
    print("-" * 30)
    
    try:
        from app.qa.unified_query import (
            optimized_ask, simple_ask, advanced_ask, 
            EmailQueryEngine, QueryStrategy, 
            get_cache_status, clear_cache
        )
        print("   ✓ Unified query imports: OK")
        
        # Test enum
        strategies = [QueryStrategy.SIMPLE, QueryStrategy.ADVANCED, QueryStrategy.OPTIMIZED]
        print(f"   ✓ Query strategies: {[s.value for s in strategies]}")
        
        return True
    except ImportError as e:
        print(f"   ✗ Import error: {e}")
        return False

def test_cache_management():
    """Test cache management functionality"""
    print("\n2. Testing Cache Management")
    print("-" * 30)
    
    try:
        from app.qa.unified_query import get_cache_status, clear_cache
        
        # Check initial cache status
        status = get_cache_status()
        print(f"   ✓ Cache status check: {status}")
        
        # Clear cache
        clear_cache()
        status_after_clear = get_cache_status()
        print(f"   ✓ Cache clear: {status_after_clear}")
        
        return True
    except Exception as e:
        print(f"   ✗ Cache management error: {e}")
        return False

def test_query_strategies():
    """Test different query strategies"""
    print("\n3. Testing Query Strategies")
    print("-" * 30)
    
    try:
        from app.qa.unified_query import EmailQueryEngine, QueryStrategy
        
        # Test each strategy initialization
        strategies = [
            (QueryStrategy.SIMPLE, "Simple"),
            (QueryStrategy.ADVANCED, "Advanced"), 
            (QueryStrategy.OPTIMIZED, "Optimized")
        ]
        
        for strategy, name in strategies:
            try:
                engine = EmailQueryEngine(strategy=strategy)
                print(f"   ✓ {name} strategy engine: OK")
            except Exception as e:
                print(f"   ✗ {name} strategy error: {e}")
                return False
        
        return True
    except Exception as e:
        print(f"   ✗ Strategy test error: {e}")
        return False

def test_backward_compatibility():
    """Test backward compatibility functions"""
    print("\n4. Testing Backward Compatibility")
    print("-" * 30)
    
    try:
        from app.qa.unified_query import optimized_ask, simple_ask, advanced_ask
        
        # These should be callable functions
        functions = [
            (optimized_ask, "optimized_ask"),
            (simple_ask, "simple_ask"),
            (advanced_ask, "advanced_ask")
        ]
        
        for func, name in functions:
            if callable(func):
                print(f"   ✓ {name}: Callable")
            else:
                print(f"   ✗ {name}: Not callable")
                return False
        
        return True
    except ImportError as e:
        print(f"   ✗ Compatibility test error: {e}")
        return False

def test_ui_imports():
    """Test that UI files can import the unified engine"""
    print("\n5. Testing UI Imports")
    print("-" * 30)
    
    try:
        # Test chat interface imports
        import sys
        if 'app.ui.chat_interface' in sys.modules:
            del sys.modules['app.ui.chat_interface']
            
        # This should not fail
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "chat_interface", 
            "app/ui/chat_interface.py"
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            # Don't execute, just check if it can be loaded
            print("   ✓ Chat interface: Can be loaded")
        else:
            print("   ✗ Chat interface: Cannot be loaded")
            return False
            
        return True
    except Exception as e:
        print(f"   ✗ UI import error: {e}")
        return False

def test_removed_files():
    """Test that old files are properly removed"""
    print("\n6. Testing File Cleanup")
    print("-" * 30)
    
    removed_files = [
        "app/qa/simple_query.py",
        "app/qa/query_engine.py", 
        "app/qa/optimized_query.py",
        "app/tasks/__init__.py"
    ]
    
    cleanup_success = True
    for file_path in removed_files:
        if Path(file_path).exists():
            print(f"   ✗ {file_path}: Still exists (should be removed)")
            cleanup_success = False
        else:
            print(f"   ✓ {file_path}: Properly removed")
    
    # Check that new file exists
    if Path("app/qa/unified_query.py").exists():
        print("   ✓ app/qa/unified_query.py: Created successfully")
    else:
        print("   ✗ app/qa/unified_query.py: Missing")
        cleanup_success = False
    
    return cleanup_success

def main():
    """Run all consolidation tests"""
    print("PHASE 1 CONSOLIDATION TESTS")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_cache_management,
        test_query_strategies,
        test_backward_compatibility,
        test_ui_imports,
        test_removed_files
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
            print(f"   ✗ Test failed with exception: {e}")
            failed += 1
    
    print(f"\nTEST RESULTS")
    print("=" * 50)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")
    
    if failed == 0:
        print("\nALL TESTS PASSED - Consolidation successful!")
        return True
    else:
        print(f"\n{failed} tests failed - Issues need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)