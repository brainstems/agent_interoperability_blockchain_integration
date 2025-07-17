"""
State Agent Implementation

This module provides the StateAgent class which is responsible for managing
and maintaining state across the system with distributed lock support,
event sourcing, and conflict resolution.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic, Tuple
from enum import Enum

from .base_agent import InfrastructureBaseAgent

# Type definitions for better type hints
T = TypeVar('T')
StateKey = Union[str, tuple]
StateValue = Any
StateUpdate = Dict[str, Any]

class StateOperation(Enum):
    """Enumeration of state operations."""
    GET = "get"
    SET = "set"
    DELETE = "delete"
    INCREMENT = "increment"
    EXPIRE = "expire"
    EXISTS = "exists"
    KEYS = "keys"

class StateEvent:
    """Represents a state change event."""
    
    def __init__(self, 
                 event_id: str,
                 operation: StateOperation,
                 key: StateKey,
                 value: Optional[Any] = None,
                 timestamp: float = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.event_id = event_id
        self.operation = operation
        self.key = key
        self.value = value
        self.timestamp = timestamp or time.time()
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "event_id": self.event_id,
            "operation": self.operation.value,
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }

class StateAgent(InfrastructureBaseAgent[Dict[str, Any], Dict[str, Any]]):
    """
    An agent responsible for managing and maintaining system state.
    
    The StateAgent provides a centralized way to store, retrieve, and manage
    state across different components of the system. It supports:
    - Distributed locking
    - Event sourcing
    - Conflict resolution
    - State snapshots
    - Versioning
    """
    
    name = "StateAgent"
    description = "Manages and maintains system state with distributed capabilities"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the StateAgent.
        
        Args:
            config: Configuration dictionary for the agent
        """
        default_config = {
            "storage_backend": "redis",  # Options: memory, redis, database, etc.
            "default_ttl": 3600,  # Default time-to-live in seconds
            "namespace": "default",  # Namespace for state keys
            "redis_url": "redis://localhost:6379/0",  # Redis connection URL
            "lock_timeout": 30,  # Lock timeout in seconds
            "event_retention": 86400,  # Event retention in seconds (24 hours)
            "snapshot_interval": 3600,  # Snapshot interval in seconds (1 hour)
            "conflict_strategy": "last_write_wins"  # Options: last_write_wins, optimistic_lock
        }
        
        # Merge provided config with defaults
        if config:
            default_config.update(config)
            
        super().__init__(default_config)
        
        # Initialize state storage
        self._storage = {}
        self._initialize_storage()
        
        # Initialize event store
        self._event_store = {}
        self._event_lock = asyncio.Lock()
        
        # Initialize snapshot management
        self._last_snapshot_time = 0
        self._snapshot_lock = asyncio.Lock()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _initialize_storage(self) -> None:
        """Initialize the state storage backend."""
        backend = self.config["storage_backend"]
        
        if backend == "memory":
            self._storage = {}
        elif backend == "redis":
            try:
                import redis.asyncio as redis
                self._storage = redis.Redis.from_url(
                    self.config["redis_url"],
                    decode_responses=True
                )
                # Initialize event store
                self._event_store = redis.Redis.from_url(
                    self.config["redis_url"],
                    decode_responses=True,
                    db=1  # Use separate DB for events
                )
            except ImportError:
                self.logger.warning(
                    "Redis not available. Falling back to in-memory storage."
                )
                self._storage = {}
                self._event_store = {}
        else:
            self.logger.warning(
                f"Unsupported storage backend: {backend}. Using in-memory storage."
            )
            self._storage = {}
            self._event_store = {}
    
    def _get_full_key(self, key: StateKey) -> str:
        """
        Get the full namespaced key.
        
        Args:
            key: The base key
            
        Returns:
            The full namespaced key
        """
        namespace = self.config["namespace"]
        if isinstance(key, (list, tuple)):
            key = ":".join(str(k) for k in key)
        return f"{namespace}:{key}"
    
    def _get_lock_key(self, key: StateKey) -> str:
        """
        Get the lock key for distributed locking.
        
        Args:
            key: The state key to lock
            
        Returns:
            The lock key
        """
        return f"lock:{self._get_full_key(key)}"
    
    async def _acquire_lock(self, key: StateKey, timeout: int = None) -> bool:
        """
        Acquire a distributed lock for the given key.
        
        Args:
            key: The key to lock
            timeout: Optional timeout in seconds
            
        Returns:
            True if lock was acquired, False otherwise
        """
        lock_key = self._get_lock_key(key)
        timeout = timeout or self.config["lock_timeout"]
        
        if isinstance(self._storage, dict):
            # In-memory lock
            if lock_key in self._storage:
                return False
            self._storage[lock_key] = time.time()
            return True
        else:
            # Redis lock
            return await self._storage.set(
                lock_key,
                time.time(),
                ex=timeout,
                nx=True
            )
    
    async def _release_lock(self, key: StateKey) -> bool:
        """
        Release a distributed lock for the given key.
        
        Args:
            key: The key to unlock
            
        Returns:
            True if lock was released, False otherwise
        """
        lock_key = self._get_lock_key(key)
        
        if isinstance(self._storage, dict):
            # In-memory lock
            if lock_key in self._storage:
                del self._storage[lock_key]
                return True
            return False
        else:
            # Redis lock
            return await self._storage.delete(lock_key) > 0
    
    async def _record_event(self, event: StateEvent) -> None:
        """
        Record a state change event.
        
        Args:
            event: The event to record
        """
        async with self._event_lock:
            event_key = f"events:{event.event_id}"
            
            if isinstance(self._event_store, dict):
                self._event_store[event_key] = event.to_dict()
            else:
                await self._event_store.set(
                    event_key,
                    json.dumps(event.to_dict()),
                    ex=self.config["event_retention"]
                )
    
    async def _create_snapshot(self) -> None:
        """
        Create a state snapshot.
        """
        async with self._snapshot_lock:
            snapshot_id = str(uuid.uuid4())
            snapshot_key = f"snapshot:{snapshot_id}"
            
            # Get current state
            state = {}
            if isinstance(self._storage, dict):
                state = self._storage.copy()
            else:
                # Get all keys from Redis
                keys = await self._storage.keys(f"{self.config['namespace']}:*")
                for key in keys:
                    state[key] = await self._storage.get(key)
            
            # Store snapshot
            if isinstance(self._event_store, dict):
                self._event_store[snapshot_key] = {
                    "id": snapshot_id,
                    "timestamp": time.time(),
                    "state": state
                }
            else:
                await self._event_store.set(
                    snapshot_key,
                    json.dumps({
                        "id": snapshot_id,
                        "timestamp": time.time(),
                        "state": state
                    }),
                    ex=self.config["event_retention"]
                )
    
    def _start_background_tasks(self):
        """Start background tasks for snapshots and cleanup."""
        asyncio.create_task(self._snapshot_task())
        asyncio.create_task(self._cleanup_task())
    
    async def _snapshot_task(self):
        """Periodically create state snapshots."""
        while True:
            try:
                if time.time() - self._last_snapshot_time >= self.config["snapshot_interval"]:
                    await self._create_snapshot()
                    self._last_snapshot_time = time.time()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in snapshot task: {e}", exc_info=True)
    
    async def _cleanup_task(self):
        """Periodically clean up old events and snapshots."""
        while True:
            try:
                # Get all events
                if isinstance(self._event_store, dict):
                    # In-memory cleanup
                    current_time = time.time()
                    for key, value in list(self._event_store.items()):
                        if key.startswith("events:"):
                            event = json.loads(value)
                            if current_time - event["timestamp"] > self.config["event_retention"]:
                                del self._event_store[key]
                else:
                    # Redis cleanup
                    keys = await self._event_store.keys("events:*")
                    for key in keys:
                        event = json.loads(await self._event_store.get(key))
                        if time.time() - event["timestamp"] > self.config["event_retention"]:
                            await self._event_store.delete(key)
                
                await asyncio.sleep(3600)  # Clean up every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}", exc_info=True)
    
    async def _process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a state management request with distributed capabilities.
        
        Args:
            request: The state management request
            
        Returns:
            A dictionary containing the response
            
        Raises:
            ValueError: If the request is invalid
        """
        action = request.get("action")
        key = request.get("key")
        value = request.get("value")
        ttl = request.get("ttl", self.config["default_ttl"])
        
        if not action:
            return self._error_response("No action specified")
            
        # Acquire lock
        if not await self._acquire_lock(key):
            return self._error_response("Could not acquire lock")
            
        try:
            # Create event
            event = StateEvent(
                event_id=str(uuid.uuid4()),
                operation=StateOperation(action.upper()),
                key=key,
                value=value,
                metadata={"ttl": ttl}
            )
            
            # Process action
            if action == "get":
                result = await self.get(key)
            elif action == "set":
                result = await self.set(key, value, ttl=ttl)
            elif action == "delete":
                result = await self.delete(key)
            elif action == "increment":
                result = await self.increment(key, value or 1)
            elif action == "expire":
                result = await self.expire(key, ttl)
            elif action == "exists":
                result = await self.exists(key)
            elif action == "keys":
                pattern = request.get("pattern", "*")
                result = await self.keys(pattern)
            else:
                return self._error_response(f"Unknown action: {action}")
                
            # Record event
            await self._record_event(event)
            
            return {
                "success": True,
                "action": action,
                "key": key,
                "result": result,
                "event_id": event.event_id,
                "timestamp": event.timestamp
            }
            
        except Exception as e:
            self.logger.error(f"Error processing {action} request: {e}", exc_info=True)
            return self._error_response(str(e))
            
        finally:
            # Release lock
            await self._release_lock(key)
    
    async def get_state_history(self, key: StateKey) -> List[Dict[str, Any]]:
        """
        Get the history of state changes for a key.
        
        Args:
            key: The key to get history for
            
        Returns:
            List of state change events
        """
        events = []
        
        if isinstance(self._event_store, dict):
            for event_id, event_data in self._event_store.items():
                if event_data.get("key") == key:
                    events.append(event_data)
        else:
            # Get all events for this key
            keys = await self._event_store.keys(f"events:*")
            for key in keys:
                event_data = json.loads(await self._event_store.get(key))
                if event_data.get("key") == key:
                    events.append(event_data)
        
        return sorted(events, key=lambda x: x["timestamp"])
    
    async def get_snapshot(self, snapshot_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Get a state snapshot.
        
        Args:
            snapshot_id: Optional snapshot ID to retrieve
            
        Returns:
            The snapshot data if found, None otherwise
        """
        if snapshot_id:
            snapshot_key = f"snapshot:{snapshot_id}"
        else:
            # Get latest snapshot
            keys = await self._event_store.keys("snapshot:*")
            if not keys:
                return None
                
            # Get the latest snapshot
            snapshot_key = max(keys)
            
        if isinstance(self._event_store, dict):
            return self._event_store.get(snapshot_key)
        else:
            data = await self._event_store.get(snapshot_key)
            return json.loads(data) if data else None
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            message: The error message
            
        Returns:
            An error response dictionary
        """
        return {
            "success": False,
            "error": message,
            "timestamp": time.time()
        }
    
    async def get(self, key: StateKey) -> Optional[StateValue]:
        """
        Get a value from the state store.
        
        Args:
            key: The key to get
            
        Returns:
            The value associated with the key, or None if not found
        """
        full_key = self._get_full_key(key)
        
        if isinstance(self._storage, dict):
            item = self._storage.get(full_key)
            if item is None:
                return None
                
            # Check if the item has expired
            if "expires" in item and item["expires"] < time.time():
                del self._storage[full_key]
                return None
                
            return item["value"]
        else:
            # Handle Redis or other backends
            value = await self._storage.get(full_key)
            if value is None:
                return None
                
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
    
    async def set(self, key: StateKey, value: StateValue, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the state store.
        
        Args:
            key: The key to set
            value: The value to store
            ttl: Optional time-to-live in seconds
            
        Returns:
            True if the operation was successful
        """
        full_key = self._get_full_key(key)
        
        if ttl is None:
            ttl = self.config["default_ttl"]
        
        if isinstance(self._storage, dict):
            item = {
                "value": value,
                "created_at": time.time()
            }
            
            if ttl > 0:
                item["expires"] = time.time() + ttl
                
            self._storage[full_key] = item
            return True
        else:
            # Handle Redis or other backends
            serialized = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            if ttl > 0:
                return await self._storage.setex(full_key, ttl, serialized)
            else:
                return await self._storage.set(full_key, serialized)
    
    async def delete(self, key: StateKey) -> bool:
        """
        Delete a key from the state store.
        
        Args:
            key: The key to delete
            
        Returns:
            True if the key was deleted, False if it didn't exist
        """
        full_key = self._get_full_key(key)
        
        if isinstance(self._storage, dict):
            if full_key in self._storage:
                del self._storage[full_key]
                return True
            return False
        else:
            return await self._storage.delete(full_key) > 0
    
    async def increment(self, key: StateKey, amount: int = 1) -> int:
        """
        Increment a numeric value in the state store.
        
        Args:
            key: The key to increment
            amount: The amount to increment by
            
        Returns:
            The new value
        """
        current = await self.get(key) or 0
        if not isinstance(current, (int, float)):
            raise ValueError(f"Cannot increment non-numeric value: {current}")
            
        new_value = current + amount
        await self.set(key, new_value)
        return new_value
    
    async def expire(self, key: StateKey, ttl: int) -> bool:
        """
        Set an expiration time on a key.
        
        Args:
            key: The key to set the TTL for
            ttl: Time-to-live in seconds
            
        Returns:
            True if the timeout was set
        """
        full_key = self._get_full_key(key)
        
        if isinstance(self._storage, dict):
            if full_key in self._storage:
                self._storage[full_key]["expires"] = time.time() + ttl
                return True
            return False
        else:
            return await self._storage.expire(full_key, ttl)
    
    async def exists(self, key: StateKey) -> bool:
        """
        Check if a key exists in the state store.
        
        Args:
            key: The key to check
            
        Returns:
            True if the key exists, False otherwise
        """
        full_key = self._get_full_key(key)
        
        if isinstance(self._storage, dict):
            return full_key in self._storage
        else:
            return await self._storage.exists(full_key) > 0
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """
        Find all keys matching a pattern.
        
        Args:
            pattern: The pattern to match keys against
            
        Returns:
            A list of matching keys
        """
        full_pattern = self._get_full_key(pattern)
        
        if isinstance(self._storage, dict):
            import fnmatch
            return [k for k in self._storage.keys() if fnmatch.fnmatch(k, full_pattern)]
        else:
            # For Redis
            keys = await self._storage.keys(full_pattern)
            # Remove namespace for consistency
            namespace = self.config["namespace"] + ":"
            return [k[len(namespace):] for k in keys]
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            message: The error message
            
        Returns:
            An error response dictionary
        """
        return {
            "success": False,
            "error": message
        }
    
    async def _shutdown(self) -> None:
        """Clean up resources used by the agent."""
        self.logger.info("Shutting down StateAgent")
        if hasattr(self._storage, 'close'):
            await self._storage.close()
