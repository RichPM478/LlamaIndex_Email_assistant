#!/usr/bin/env python3
"""
Test that chat interface works with lazy query engine
"""

def test_chat_interface_imports():
    """Test that chat interface imports work correctly"""
    print("TESTING CHAT INTERFACE COMPATIBILITY")
    print("=" * 50)
    
    try:
        # Test the exact imports used by chat interface
        from app.qa.lazy_query import lazy_optimized_ask as optimized_ask, get_cache_status
        
        print("[OK] Chat interface imports successful")
        
        # Test cache status has expected keys
        status = get_cache_status()
        expected_keys = ["llm_loaded", "embed_model_loaded", "index_loaded", "settings_loaded"]
        
        for key in expected_keys:
            if key in status:
                print(f"[OK] Cache status has '{key}': {status[key]}")
            else:
                print(f"[ERROR] Cache status missing '{key}'")
                return False
        
        print(f"[OK] Cache status: {status}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Chat interface test failed: {e}")
        return False

def test_streamlit_compatibility():
    """Test streamlit app imports"""
    print("\nTESTING STREAMLIT APP COMPATIBILITY")
    print("=" * 50)
    
    try:
        # Test the exact imports used by streamlit app
        from app.qa.lazy_query import lazy_optimized_ask as ask
        
        print("[OK] Streamlit app imports successful")
        return True
        
    except Exception as e:
        print(f"[ERROR] Streamlit app test failed: {e}")
        return False

if __name__ == "__main__":
    success1 = test_chat_interface_imports()
    success2 = test_streamlit_compatibility()
    
    if success1 and success2:
        print("\n[SUCCESS] All interface compatibility tests passed!")
        print("Chat interface and Streamlit app should work correctly.")
    else:
        print("\n[ERROR] Some compatibility tests failed!")
    
    exit(0 if success1 and success2 else 1)