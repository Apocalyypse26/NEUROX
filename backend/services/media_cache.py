import hashlib
import tempfile
import os
import asyncio
from typing import Tuple, Optional
import httpx
from .tribe_service import is_url_safe
from .retry import retry_with_backoff

class MediaCache:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="neurox_cache_")
        self._cache = {}
        self._lock = asyncio.Lock()
        self._downloading = {}  # Track in-flight downloads to prevent duplicates
    
    async def get_or_download(self, url: str) -> Tuple[bytes, str]:
        """Download media once, cache for reuse. Thread-safe with lock."""
        if url in self._cache:
            return self._cache[url]
        
        # If another request is already downloading this URL, wait for it
        if url in self._downloading:
            return await self._downloading[url]
        
        if not is_url_safe(url):
            raise ValueError(f"URL not allowed: {url}")
        
        async def _download():
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.content
        
        # Create a future that other concurrent callers can await
        download_future = asyncio.ensure_future(retry_with_backoff(_download))
        self._downloading[url] = download_future
        
        try:
            data = await download_future
        finally:
            self._downloading.pop(url, None)
        
        cache_key = hashlib.md5(url.encode()).hexdigest()
        cache_path = f"{self.temp_dir}/{cache_key}"
        
        with open(cache_path, 'wb') as f:
            f.write(data)
        
        async with self._lock:
            self._cache[url] = (data, cache_path)
        return data, cache_path
    
    async def cleanup_file(self, path: str):
        """Clean up a specific cached file"""
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
    
    def cleanup_all(self):
        """Clean up entire cache"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self._cache.clear()

media_cache = MediaCache()