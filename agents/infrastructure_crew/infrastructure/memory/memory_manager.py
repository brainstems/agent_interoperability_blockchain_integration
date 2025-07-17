"""
Memory Manager Implementation

This module provides the MemoryManager class which manages shared memory across
the infrastructure crew. It handles memory allocation, monitoring, and cleanup
across different teams and agents.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
# from enum import Enum # No longer needed directly here for these
import psutil
import platform
from redis.asyncio import Redis
from datetime import datetime, timezone # For new event payloads

from agents.infrastructure_crew.schemas.event_schemas import (
    BaseEvent,
    EventPriority,
    MemoryEventType as StandardMemoryEventType,
    MemoryPressureLevel as StandardMemoryPressureLevel,
    MemoryUsageStatsPayload,
    MemoryUsageEventPayload,
    MemoryUsageEvent,
    MemoryPressureEventPayload,
    MemoryPressureEvent,
    MemoryCleanupTriggeredEventPayload,
    MemoryCleanupTriggeredEvent,
    MemoryCleanupCompletedEventPayload,
    MemoryCleanupCompletedEvent,
    MemoryEvictionEventPayload,
    MemoryEvictionEvent
)

# Local MemoryEventType and MemoryPressureLevel enums are removed.
# We will use StandardMemoryEventType and StandardMemoryPressureLevel from schemas.

class MemoryUsage:
    """Represents memory usage statistics."""
    
    def __init__(self):
        self.total: int = 0
        self.available: int = 0
        self.used: int = 0
        self.free: int = 0
        self.percent: float = 0.0
        self.update()
        
    def update(self) -> None:
        """Update memory usage statistics."""
        mem = psutil.virtual_memory()
        self.total = mem.total
        self.available = mem.available
        self.used = mem.used
        self.free = mem.free
        self.percent = mem.percent
        
    def to_payload(self) -> MemoryUsageStatsPayload:
        """Convert to MemoryUsageStatsPayload format."""
        return MemoryUsageStatsPayload(
            total_bytes=self.total,
            available_bytes=self.available,
            used_bytes=self.used,
            free_bytes=self.free, # Assuming this maps well
            usage_percentage=self.percent
        )

# MemoryPressureLevel enum is now imported as StandardMemoryPressureLevel

class MemoryManager:
    """
    Manages shared memory across the infrastructure crew.
    
    The MemoryManager provides centralized memory management, monitoring,
    and cleanup services for all infrastructure agents and teams.
    """
    
    def __init__(self, config: Dict[str, Any], redis_client=None, crew_manager=None):
        """
        Initialize the MemoryManager.
        
        Args:
            config: Configuration dictionary for the manager
            redis_client: Optional Redis client instance (for testing)
            crew_manager: Optional CrewManager instance for event distribution
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._usage = MemoryUsage()
        self._cleanup_tasks: List[asyncio.Task] = []
        self._cleanup_lock = asyncio.Lock()
        self._eviction_lock = asyncio.Lock()
        self._metrics: Dict[str, Any] = {
            "current_usage": 0,
            "peak_usage": 0,
            "evictions": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cleanup_count": 0,
            "cleanup_success": 0
        }
        
        # Initialize Redis client
        self._redis = redis_client or Redis.from_url(self.config.get("redis_url", "redis://localhost:6379/0"))
        
        # Initialize memory thresholds
        self._thresholds = {
            "low": self.config.get("low_threshold", 0.7),
            "medium": self.config.get("medium_threshold", 0.8),
            "high": self.config.get("high_threshold", 0.9),
            "critical": self.config.get("critical_threshold", 0.95)
        }
        
        # Initialize monitoring
        self._monitor_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Set crew manager
        self._crew_manager = crew_manager

        # Periodic cleanup interval
        self._periodic_cleanup_interval = self.config.get("periodic_cleanup_interval_seconds", 6 * 60 * 60) # Default to 6 hours
        
    async def initialize(self):
        """
        Initialize memory monitoring and cleanup tasks.
        """
        try:
            # Verify Redis connection
            if not await self._redis.ping():
                raise ConnectionError("Redis connection failed")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Redis: {str(e)}")
            
        # Initialize monitoring
        self._monitor_task = asyncio.create_task(self._monitor_memory())
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
    async def _monitor_memory(self):
        """
        Continuously monitor memory usage and trigger cleanup if needed.
        """
        while True:
            try:
                self._usage.update()
                usage = self._usage.percent / 100
                
                # Update metrics
                self._metrics["current_usage"] = usage
                self._metrics["peak_usage"] = max(self._metrics["peak_usage"], usage)
                
                # Check pressure level
                pressure_level = self._get_pressure_level(usage)
                
                # Prepare and distribute memory usage event
                stats_payload = self._usage.to_payload()
                usage_event_payload = MemoryUsageEventPayload(
                    stats=stats_payload,
                    pressure_level=pressure_level # Already a StandardMemoryPressureLevel enum
                    # timestamp is handled by MemoryUsageEventPayload default_factory
                )
                usage_event = MemoryUsageEvent(
                    payload=usage_event_payload,
                    source_entity_id="MemoryManager"
                    # event_id, event_type, timestamp are handled by BaseEvent/MemoryUsageEvent
                )
                await self._distribute_memory_event(usage_event)
                
                # Handle memory pressure
                if pressure_level != StandardMemoryPressureLevel.LOW:
                    await self.handle_memory_pressure(pressure_level)
                
                await asyncio.sleep(self.config.get("monitor_interval", 60))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring memory: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait before retrying
    
    def _get_pressure_level(self, usage: float) -> StandardMemoryPressureLevel:
        """
        Determine the current memory pressure level.
        
        Args:
            usage: Current memory usage as a fraction (0-1)
            
        Returns:
            The current memory pressure level
        """
        if usage >= self._thresholds["critical"]:
            return StandardMemoryPressureLevel.CRITICAL
        elif usage >= self._thresholds["high"]:
            return StandardMemoryPressureLevel.HIGH
        elif usage >= self._thresholds["medium"]:
            return StandardMemoryPressureLevel.MEDIUM
        return StandardMemoryPressureLevel.LOW
    
    async def handle_memory_pressure(self, level: StandardMemoryPressureLevel) -> None:
        """
        Handle memory pressure by triggering cleanup operations.
        
        Args:
            level: The current memory pressure level
            """
        async with self._cleanup_lock:
            try:
                self.logger.info(f"Handling memory pressure level: {level}")
                
                # Prepare and distribute pressure event
                pressure_event_payload = MemoryPressureEventPayload(
                    pressure_level=level,
                    message=f"Memory pressure at {level.value} level.",
                    details={"current_usage_percent": self._usage.percent}
                    # timestamp is handled by MemoryPressureEventPayload default_factory
                )
                pressure_event = MemoryPressureEvent(
                    payload=pressure_event_payload,
                    source_entity_id="MemoryManager"
                    # event_id, event_type, timestamp, priority are handled by BaseEvent/MemoryPressureEvent
                )
                await self._distribute_memory_event(pressure_event)
                
                # Trigger cleanup operations based on pressure level
                if level == StandardMemoryPressureLevel.CRITICAL:
                    await self._critical_cleanup()
                elif level == StandardMemoryPressureLevel.HIGH:
                    await self._high_cleanup()
                elif level == StandardMemoryPressureLevel.MEDIUM:
                    await self._medium_cleanup()
                
                self._metrics["cleanup_count"] += 1
                
            except Exception as e:
                self.logger.error(f"Error handling memory pressure: {e}", exc_info=True)
    
    async def _critical_cleanup(self):
        """Perform critical cleanup operations."""
        start_time = time.monotonic()
        errors_encountered_cleanup = []
        bytes_freed_total = 0
        strategies_applied_list = ["evict_least_used", "compress_state", "cleanup_old_events"]

        triggered_payload = MemoryCleanupTriggeredEventPayload(
            strategy_used="critical_cleanup_strategy"
        )
        triggered_event = MemoryCleanupTriggeredEvent(payload=triggered_payload, source_entity_id="MemoryManager")
        await self._distribute_memory_event(triggered_event)

        try:
            # Placeholder estimations for bytes freed
            await self._evict_least_used() 
            bytes_freed_total += 50000 # Placeholder for bytes freed by _evict_least_used
            await self._compress_state()
            bytes_freed_total += 30000 # Placeholder for bytes freed by _compress_state
            await self._cleanup_old_events()
            bytes_freed_total += 20000 # Placeholder for bytes freed by _cleanup_old_events
            
            self._metrics["cleanup_success"] += 1 # Increment only if all operations succeed
        except Exception as e:
            self.logger.error(f"Error during critical cleanup: {e}", exc_info=True)
            errors_encountered_cleanup.append(str(e))
        finally:
            duration = time.monotonic() - start_time
            completed_payload = MemoryCleanupCompletedEventPayload(
                bytes_freed=bytes_freed_total,
                duration_seconds=duration,
                strategies_applied=strategies_applied_list,
                errors_encountered=errors_encountered_cleanup if errors_encountered_cleanup else None
            )
            completed_event = MemoryCleanupCompletedEvent(payload=completed_payload, source_entity_id="MemoryManager")
            await self._distribute_memory_event(completed_event)
        
    async def _high_cleanup(self):
        """Perform high priority cleanup operations."""
        start_time = time.monotonic()
        errors_encountered_cleanup = []
        bytes_freed_total = 0
        strategies_applied_list = ["evict_least_used", "cleanup_old_events"]

        triggered_payload = MemoryCleanupTriggeredEventPayload(strategy_used="high_cleanup_strategy")
        triggered_event = MemoryCleanupTriggeredEvent(payload=triggered_payload, source_entity_id="MemoryManager")
        await self._distribute_memory_event(triggered_event)

        try:
            await self._evict_least_used()
            bytes_freed_total += 40000 # Placeholder
            await self._cleanup_old_events()
            bytes_freed_total += 15000 # Placeholder

            self._metrics["cleanup_success"] += 1
        except Exception as e:
            self.logger.error(f"Error during high cleanup: {e}", exc_info=True)
            errors_encountered_cleanup.append(str(e))
        finally:
            duration = time.monotonic() - start_time
            completed_payload = MemoryCleanupCompletedEventPayload(
                bytes_freed=bytes_freed_total,
                duration_seconds=duration,
                strategies_applied=strategies_applied_list,
                errors_encountered=errors_encountered_cleanup if errors_encountered_cleanup else None
            )
            completed_event = MemoryCleanupCompletedEvent(payload=completed_payload, source_entity_id="MemoryManager")
            await self._distribute_memory_event(completed_event)
        
    async def _medium_cleanup(self):
        """Perform medium priority cleanup operations."""
        start_time = time.monotonic()
        errors_encountered_cleanup = []
        bytes_freed_total = 0
        strategies_applied_list = ["cleanup_old_events"]

        triggered_payload = MemoryCleanupTriggeredEventPayload(strategy_used="medium_cleanup_strategy")
        triggered_event = MemoryCleanupTriggeredEvent(payload=triggered_payload, source_entity_id="MemoryManager")
        await self._distribute_memory_event(triggered_event)

        try:
            await self._cleanup_old_events()
            bytes_freed_total += 10000 # Placeholder

            self._metrics["cleanup_success"] += 1
        except Exception as e:
            self.logger.error(f"Error during medium cleanup: {e}", exc_info=True)
            errors_encountered_cleanup.append(str(e))
        finally:
            duration = time.monotonic() - start_time
            completed_payload = MemoryCleanupCompletedEventPayload(
                bytes_freed=bytes_freed_total,
                duration_seconds=duration,
                strategies_applied=strategies_applied_list,
                errors_encountered=errors_encountered_cleanup if errors_encountered_cleanup else None
            )
            completed_event = MemoryCleanupCompletedEvent(payload=completed_payload, source_entity_id="MemoryManager")
            await self._distribute_memory_event(completed_event)
    
    async def _evict_least_used(self):
        """Evict least used items from cache."""
        async with self._eviction_lock:
            try:
                # Placeholder for actual eviction strategy and item identification
                evicted_ids_placeholder = [f"item_evicted_{i+1}_{int(time.time())}" for i in range(2)] # Example dynamic IDs
                bytes_freed_by_eviction_placeholder = 50 * 1024  # Example: 50KB
                eviction_reason_placeholder = "Evicted due to memory pressure or routine cleanup."

                if not evicted_ids_placeholder:
                    self.logger.info("No items to evict or eviction strategy yielded no items.")
                    return

                self._metrics["evictions"] += len(evicted_ids_placeholder)
                
                # Distribute eviction event
                eviction_event_payload = MemoryEvictionEventPayload(
                    evicted_item_ids=evicted_ids_placeholder,
                    bytes_freed=bytes_freed_by_eviction_placeholder,
                    reason=eviction_reason_placeholder
                    # timestamp is handled by MemoryEvictionEventPayload default_factory
                )
                eviction_event = MemoryEvictionEvent(
                    payload=eviction_event_payload,
                    source_entity_id="MemoryManager"
                    # event_id, event_type, timestamp, priority are handled by BaseEvent/MemoryEvictionEvent
                )
                await self._distribute_memory_event(eviction_event)
                self.logger.info(f"Evicted {len(evicted_ids_placeholder)} items, freeing {bytes_freed_by_eviction_placeholder} bytes.")
                
            except Exception as e:
                self.logger.error(f"Error evicting items: {e}", exc_info=True)
    
    async def _compress_state(self):
        """Compress state data to reduce memory usage."""
        try:
            # Implement state compression
            pass
            
        except Exception as e:
            self.logger.error(f"Error compressing state: {e}", exc_info=True)
    
    async def _cleanup_old_events(self):
        """Cleanup old events from memory."""
        try:
            # Implement event cleanup
            pass
            
        except Exception as e:
            self.logger.error(f"Error cleaning up events: {e}", exc_info=True)
    
    async def _distribute_memory_event(self, event: BaseEvent) -> None:
        """
        Distribute memory-related events.
        
        Args:
            event: The fully formed event object (e.g., MemoryUsageEvent).
        """
        # Event object is already created and typed (e.g., MemoryUsageEvent)
        # It includes event_id, event_type, timestamp, source_entity_id, payload, and priority.
        
        # Distribute event via CrewManager or Redis
        if self._crew_manager:
            # Assuming crew_manager.distribute_event can handle BaseEvent Pydantic models
            await self._crew_manager.distribute_event(event)
        else:
            # Fallback: publish to Redis
            # Event type is part of the event object (event.event_type)
            channel = f"memory_events:{event.event_type}"
            await self._redis.publish(channel, event.model_dump_json())
            self.logger.debug(f"Published event to Redis channel {channel}: {event.event_id}")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get current memory management metrics.
        
        Returns:
            Dictionary of memory metrics
        """
        return self._metrics.copy()
    
    async def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get current memory usage statistics.
        """
        self._usage.update()
        return self._usage.to_payload().model_dump()
    
    async def _periodic_cleanup(self):
        """
        Periodically triggers the cleanup process.
        """
        self.logger.info(f"Periodic cleanup task started. Interval: {self._periodic_cleanup_interval} seconds.")
        while not self._shutdown:
            try:
                await asyncio.sleep(self._periodic_cleanup_interval)
                if self._shutdown: # Re-check after sleep
                    break
                
                self.logger.info("Initiating scheduled periodic cleanup...")
                await self.trigger_cleanup(reason="periodic_maintenance", details="Scheduled periodic system cleanup.")
                
            except asyncio.CancelledError:
                self.logger.info("Periodic cleanup task cancelled.")
                break
            except Exception as e:
                self.logger.error(f"Error in periodic cleanup task: {e}", exc_info=True)
                # Wait a bit before retrying to avoid rapid-fire errors in case of persistent issues
                await asyncio.sleep(60)
        self.logger.info("Periodic cleanup task finished.")

    async def shutdown(self):
        """
        Gracefully shut down the MemoryManager.
        """
        self.logger.info("MemoryManager shutting down...")
        self._shutdown = True
        
        tasks_to_await = []
        if self._monitor_task:
            self._monitor_task.cancel()
            tasks_to_await.append(self._monitor_task)
        
        if self._cleanup_task: # The main periodic cleanup task
            self._cleanup_task.cancel()
            tasks_to_await.append(self._cleanup_task)

        # Cancel any ongoing specific cleanup action tasks (triggered by handle_memory_pressure or trigger_cleanup)
        async with self._cleanup_lock: # Ensure no new tasks are added to self._cleanup_tasks
            for task in self._cleanup_tasks:
                if not task.done():
                    task.cancel()
                    tasks_to_await.append(task)
        
        # Wait for all tasks to complete or be cancelled
        results = await asyncio.gather(*tasks_to_await, return_exceptions=True)
        for i, result in enumerate(results):
            task_name = tasks_to_await[i].get_name() if hasattr(tasks_to_await[i], 'get_name') else f"Task-{i}"
            if isinstance(result, asyncio.CancelledError):
                self.logger.info(f"{task_name} was cancelled.")
            elif isinstance(result, Exception):
                self.logger.error(f"Error during shutdown of {task_name}: {result}", exc_info=result)

        self.logger.info("All managed tasks processed.")

        # Close Redis connection if it was created by this manager
        # This logic might need refinement based on how redis_client is typically used.
        # For now, assuming if it's not None and not passed in, we created it.
        # A better way would be to have a flag like self._created_redis_client.
        if hasattr(self, '_redis') and self._redis and not self.config.get("_redis_passed_in", False): # Assuming a hypothetical config flag
            try:
                await self._redis.close()
                # For redis-py >= 4.2.0, connection_pool.disconnect() is often called implicitly by close()
                # or might not be needed if using a single connection from from_url without explicit pool management here.
                # If using an explicit pool: await self._redis.connection_pool.disconnect()
                self.logger.info("Redis connection closed.")
            except Exception as e:
                self.logger.error(f"Error closing Redis connection: {e}")

        self.logger.info("MemoryManager shutdown complete.")
