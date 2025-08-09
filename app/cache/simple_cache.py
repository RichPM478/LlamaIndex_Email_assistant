# app/cache/simple_cache.py
import json
import os
import time
import hashlib
from typing import Any, Optional, Dict
from datetime import datetime, timedelta

class SimpleCache:
    """Simple file-based cache for frequently accessed data"""
    
    def __init__(self, cache_dir: str = "data/cache", default_ttl: int = 3600):
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl  # Time to live in seconds
        os.makedirs(cache_dir, exist_ok=True)
        
        # In-memory cache for recent items
        self.memory_cache = {}
        self.memory_cache_size = 100
    
    def _get_cache_key(self, key: str) -> str:
        """Generate a safe cache key"""
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str) -> str:
        """Get the file path for a cache key"""
        return os.path.join(self.cache_dir, f"{cache_key}.cache")
    
    def _is_expired(self, cache_file: str, ttl: int) -> bool:
        """Check if cache file is expired"""
        if not os.path.exists(cache_file):
            return True
        
        file_age = time.time() - os.path.getmtime(cache_file)
        return file_age > ttl
    
    def get(self, key: str, ttl: Optional[int] = None) -> Optional[Any]:
        """Get value from cache"""
        if ttl is None:
            ttl = self.default_ttl
        
        # Check memory cache first
        if key in self.memory_cache:
            cached_item = self.memory_cache[key]
            if time.time() - cached_item['timestamp'] < ttl:
                return cached_item['value']
            else:
                del self.memory_cache[key]
        
        # Check file cache
        cache_key = self._get_cache_key(key)
        cache_file = self._get_cache_file_path(cache_key)
        
        if self._is_expired(cache_file, ttl):
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                value = data['value']
                
                # Store in memory cache
                self._store_in_memory(key, value)
                
                return value
        except Exception as e:
            print(f"Error reading cache file {cache_file}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        if ttl is None:
            ttl = self.default_ttl
        
        # Store in memory cache
        self._store_in_memory(key, value)
        
        # Store in file cache
        cache_key = self._get_cache_key(key)
        cache_file = self._get_cache_file_path(cache_key)
        
        try:
            cache_data = {
                'value': value,
                'timestamp': time.time(),
                'ttl': ttl,
                'key': key  # Store original key for debugging
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, default=str)
                
        except Exception as e:
            print(f"Error writing cache file {cache_file}: {e}")
    
    def _store_in_memory(self, key: str, value: Any):
        """Store value in memory cache with size limit"""
        # Remove oldest items if cache is full
        if len(self.memory_cache) >= self.memory_cache_size:
            oldest_key = min(self.memory_cache.keys(), 
                           key=lambda k: self.memory_cache[k]['timestamp'])
            del self.memory_cache[oldest_key]
        
        self.memory_cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
    
    def delete(self, key: str):
        """Delete value from cache"""
        # Remove from memory cache
        if key in self.memory_cache:
            del self.memory_cache[key]
        
        # Remove from file cache
        cache_key = self._get_cache_key(key)
        cache_file = self._get_cache_file_path(cache_key)
        
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except Exception as e:
                print(f"Error removing cache file {cache_file}: {e}")
    
    def clear(self):
        """Clear all cache"""
        # Clear memory cache
        self.memory_cache.clear()
        
        # Clear file cache
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.cache'):
                    os.remove(os.path.join(self.cache_dir, filename))
        except Exception as e:
            print(f"Error clearing cache directory: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.cache')]
        
        total_size = 0
        expired_count = 0
        
        for filename in cache_files:
            file_path = os.path.join(self.cache_dir, filename)
            try:
                total_size += os.path.getsize(file_path)
                if self._is_expired(file_path, self.default_ttl):
                    expired_count += 1
            except:
                continue
        
        return {
            'memory_cache_items': len(self.memory_cache),
            'file_cache_items': len(cache_files),
            'expired_items': expired_count,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / 1024 / 1024, 2)
        }
    
    def cleanup_expired(self) -> int:
        """Remove expired cache files"""
        removed_count = 0
        
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.cache'):
                    file_path = os.path.join(self.cache_dir, filename)
                    if self._is_expired(file_path, self.default_ttl):
                        os.remove(file_path)
                        removed_count += 1
        except Exception as e:
            print(f"Error cleaning up expired cache: {e}")
        
        return removed_count

class CachedQueryEngine:
    """Wrapper for query engine with caching"""
    
    def __init__(self, query_engine_func, cache: SimpleCache):
        self.query_engine_func = query_engine_func
        self.cache = cache
        self.cache_ttl = 1800  # 30 minutes for query results
    
    def ask(self, question: str, **kwargs) -> Dict[str, Any]:
        """Ask question with caching"""
        # Create cache key from question and parameters
        cache_key = f"query:{question}:{str(sorted(kwargs.items()))}"
        
        # Try to get from cache first
        cached_result = self.cache.get(cache_key, ttl=self.cache_ttl)
        if cached_result:
            # Add cache hit indicator
            cached_result['_from_cache'] = True
            return cached_result
        
        # Execute query
        result = self.query_engine_func(question, **kwargs)
        
        # Cache the result
        result['_from_cache'] = False
        result['_cached_at'] = datetime.now().isoformat()
        self.cache.set(cache_key, result, ttl=self.cache_ttl)
        
        return result

# Global cache instance
cache = SimpleCache()

# Cached analytics functions
def get_cached_analytics(email_data_hash: str, analytics_func, *args, **kwargs):
    """Get analytics with caching"""
    cache_key = f"analytics:{email_data_hash}"
    
    cached_result = cache.get(cache_key, ttl=3600)  # 1 hour TTL for analytics
    if cached_result:
        return cached_result
    
    result = analytics_func(*args, **kwargs)
    cache.set(cache_key, result)
    
    return result