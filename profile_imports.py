#!/usr/bin/env python3
"""
Profile import performance to identify bottlenecks
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

def profile_imports():
    print("=" * 60)
    print("IMPORT PERFORMANCE PROFILING")
    print("=" * 60)
    
    # Test individual component imports
    print("\n1. CORE IMPORTS:")
    print("-" * 30)
    
    with timer("   typing imports"):
        from typing import Dict, Any, List, Optional
    
    with timer("   time import"):
        import time as time_module
    
    with timer("   re import"):
        import re
    
    print("\n2. LLAMAINDEX CORE IMPORTS:")
    print("-" * 30)
    
    with timer("   StorageContext"):
        from llama_index.core import StorageContext
    
    with timer("   load_index_from_storage"):
        from llama_index.core import load_index_from_storage
    
    with timer("   VectorStoreIndex"):
        from llama_index.core import VectorStoreIndex
    
    print("\n3. PROVIDER IMPORTS:")
    print("-" * 30)
    
    with timer("   get_settings"):
        from app.config.settings import get_settings
    
    with timer("   configure_llm"):
        from app.llm.provider import configure_llm
        
    with timer("   configure_embeddings"):
        from app.embeddings.provider import configure_embeddings
    
    print("\n4. UNIFIED QUERY ENGINE:")
    print("-" * 30)
    
    # Clear any cached modules first
    modules_to_clear = [
        'app.qa.unified_query',
    ]
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]
    
    with timer("   Unified query engine import"):
        from app.qa.unified_query import optimized_ask
    
    print("\n5. SETTINGS INITIALIZATION:")
    print("-" * 30)
    
    with timer("   Load settings"):
        settings = get_settings()
    
    print("\n6. ACTUAL MODEL LOADING (what happens on first query):")
    print("-" * 30)
    
    # This is what takes the longest time
    with timer("   LLM configuration"):
        configure_llm(settings)
    
    with timer("   Embeddings configuration"):  
        configure_embeddings(settings)
    
    with timer("   Index loading"):
        from llama_index.core import StorageContext, load_index_from_storage
        storage_context = StorageContext.from_defaults(persist_dir="data/index")
        index = load_index_from_storage(storage_context)
    
    print("\n" + "=" * 60)
    print("PROFILING COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    profile_imports()