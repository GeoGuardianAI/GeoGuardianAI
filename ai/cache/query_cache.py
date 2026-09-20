import hashlib
import time
from typing import Dict, Any, Optional

class QueryCache:
    def __init__(self):
        self.cache = {}  # hash -> {response, expires_at, metadata}
        
    def _get_hash(self, query: str, mode: str, filters: Dict[str, Any] = None) -> str:
        filter_str = json_str = ""
        if filters:
            try:
                import json
                filter_str = json.dumps(filters, sort_keys=True)
            except Exception:
                filter_str = str(filters)
        key_str = f"{query.strip().lower()}:{mode}:{filter_str}"
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
        
    def get(self, query: str, mode: str, filters: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        h = self._get_hash(query, mode, filters)
        entry = self.cache.get(h)
        if entry:
            # Check expiration (e.g. 5 minutes cache life)
            if time.time() < entry["expires_at"]:
                return entry["data"]
            else:
                # Remove expired
                del self.cache[h]
        return None
        
    def set(self, query: str, mode: str, data: Dict[str, Any], ttl_seconds: int = 300, filters: Dict[str, Any] = None):
        h = self._get_hash(query, mode, filters)
        self.cache[h] = {
            "data": data,
            "expires_at": time.time() + ttl_seconds
        }
