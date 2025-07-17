import asyncio
from typing import Dict, Any, Optional, List
from infrastructure.agents.state_agent import StateAgent, StateOperation, StateEvent
import time

class MockRedis:
    """Mock Redis client for testing."""
    
    def __init__(self):
        """Initialize mock Redis client."""
        self.data: Dict[str, Any] = {}
        self.ttl: Dict[str, float] = {}  # key -> expiration time
        self.locks: Dict[str, bool] = {}
        self._is_connected = True
        
    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a key-value pair."""
        if not self._is_connected:
            raise ConnectionError("Mock Redis is not connected")
            
        self.data[key] = value
        if ex:
            self.ttl[key] = time.time() + ex
        return True
        
    async def get(self, key: str) -> Optional[Any]:
        """Get a value by key."""
        if not self._is_connected:
            raise ConnectionError("Mock Redis is not connected")
            
        if key in self.ttl and time.time() > self.ttl[key]:
            del self.data[key]
            del self.ttl[key]
            return None
            
        return self.data.get(key)
        
    async def delete(self, key: str) -> int:
        """Delete a key."""
        if not self._is_connected:
            raise ConnectionError("Mock Redis is not connected")
            
        if key in self.data:
            if key in self.ttl:
                del self.ttl[key]
            del self.data[key]
            return 1
        return 0
        
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if not self._is_connected:
            raise ConnectionError("Mock Redis is not connected")
            
        return key in self.data and (key not in self.ttl or time.time() < self.ttl[key])
        
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching a pattern."""
        if not self._is_connected:
            raise ConnectionError("Mock Redis is not connected")
            
        return [key for key in self.data.keys()]
        
    async def incr(self, key: str) -> int:
        """Increment a key's value."""
        if not self._is_connected:
            raise ConnectionError("Mock Redis is not connected")
            
        value = self.data.get(key, 0)
        self.data[key] = value + 1
        return value + 1
        
    async def expire(self, key: str, time: int) -> bool:
        """Set a key's expiration time."""
        if not self._is_connected:
            raise ConnectionError("Mock Redis is not connected")
            
        if key in self.data:
            self.ttl[key] = time.time() + time
            return True
        return False
        
    async def lock(self, key: str, timeout: Optional[int] = None) -> bool:
        """Acquire a lock."""
        if not self._is_connected:
            raise ConnectionError("Mock Redis is not connected")
            
        if key in self.locks:
            return False
            
        self.locks[key] = True
        if timeout:
            self.ttl[key] = time.time() + timeout
        return True
        
    async def unlock(self, key: str) -> bool:
        """Release a lock."""
        if not self._is_connected:
            raise ConnectionError("Mock Redis is not connected")
            
        if key in self.locks:
            del self.locks[key]
            if key in self.ttl:
                del self.ttl[key]
            return True
        return False
        
    def close(self):
        """Close the connection."""
        self._is_connected = False
        self.data.clear()
        self.ttl.clear()
        self.locks.clear()

class MockStateAgent(StateAgent):
    """Mock StateAgent implementation for testing."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._storage = {}
        self._event_store = {}
        self._event_lock = asyncio.Lock()
        self._snapshot_lock = asyncio.Lock()
        
    async def _initialize_storage(self):
        """Initialize the storage backend."""
        self._storage = {}
        self._event_store = {}
        
    async def _start_background_tasks(self):
        """Start background tasks for snapshots and cleanup."""
        pass
        
    async def _shutdown(self):
        """Clean up resources."""
        self._storage.clear()
        self._event_store.clear()
        
    async def _record_event(self, event: StateEvent):
        """Record a state change event."""
        async with self._event_lock:
            if event.key not in self._event_store:
                self._event_store[event.key] = []
            self._event_store[event.key].append(event)
            
    async def _create_snapshot(self):
        """Create a state snapshot."""
        async with self._snapshot_lock:
            snapshot = {
                "timestamp": time.time(),
                "data": self._storage.copy()
            }
            return snapshot
        
    async def get_state_history(self, key: str):
        """Get the history of state changes for a key."""
        return self._event_store.get(key, [])
        
    async def get_snapshot(self, snapshot_id: str = None):
        """Get a state snapshot."""
        if not snapshot_id:
            return await self._create_snapshot()
        return None
        
    async def _error_response(self, message: str):
        """Create an error response."""
        return {"error": message}
        
    async def get(self, key: str):
        """Get a value from the state store."""
        return self._storage.get(key)
        
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set a value in the state store."""
        self._storage[key] = value
        if ttl:
            await self.expire(key, ttl)
        return True
        
    async def delete(self, key: str):
        """Delete a key from the state store."""
        if key in self._storage:
            del self._storage[key]
            return True
        return False
        
    async def increment(self, key: str, amount: int = 1):
        """Increment a numeric value."""
        self._storage[key] = self._storage.get(key, 0) + amount
        return self._storage[key]
        
    async def expire(self, key: str, ttl: int):
        """Set an expiration time on a key."""
        self._storage[key + ":ttl"] = time.time() + ttl
        return True
        
    async def exists(self, key: str):
        """Check if a key exists."""
        return key in self._storage
        
    async def keys(self, pattern: str = "*"):
        """Find all keys matching a pattern."""
        return [key for key in self._storage.keys()]
