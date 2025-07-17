"""
Team Memory Manager Implementation

This module provides the TeamMemoryManager class which manages memory sharing
and coordination between different teams within the infrastructure crew.

Local Setup Instructions:
1. Ensure Redis is installed and running locally
2. The default Redis URL is redis://localhost:6379/0
3. Configure memory quotas in the config dictionary
"""

import asyncio
import time
import logging
import uuid
from redis.asyncio import Redis
from typing import Dict, Any, Optional, List, Tuple, Callable
from enum import Enum # Keep for other potential enums if any
from dataclasses import dataclass # Keep if other dataclasses are used, otherwise removable
from datetime import datetime, timezone # For new event payloads
import json # For serializing/deserializing Pydantic models to/from Redis

from .team import TeamMemory # Will need refactoring later to align with TeamMemoryInfo
# from agents.infrastructure.crew_manager import Event # To be replaced by BaseEvent
from agents.infrastructure_crew.schemas.event_schemas import (
    BaseEvent,
    EventPriority,
    TeamMemoryEventType as StandardTeamMemoryEventType, # Renamed to avoid conflict if used internally
    TeamMemoryAllocationRequestPayload,
    TeamMemoryAllocationRequestEvent,
    TeamMemoryAllocationSuccessPayload,
    TeamMemoryAllocationSuccessEvent,
    TeamMemoryAllocationFailurePayload,
    TeamMemoryAllocationFailureEvent,
    TeamMemoryDeallocationRequestPayload,
    TeamMemoryDeallocationRequestEvent,
    TeamMemoryDeallocationSuccessPayload,
    TeamMemoryDeallocationSuccessEvent,
    TeamMemoryQuotaUpdatedPayload,
    TeamMemoryQuotaUpdatedEvent,
    TeamMemorySharingInitiatedPayload,
    TeamMemorySharingInitiatedEvent,
    TeamMemorySharingCompletedPayload,
    TeamMemorySharingCompletedEvent,
    TeamMemorySharingFailedPayload,
    TeamMemorySharingFailedEvent,
    TeamMemoryQuotaExceededPayload,
    TeamMemoryQuotaExceededEvent,
    TeamMemoryConflictDetectedPayload,
    TeamMemoryConflictDetectedEvent,
    TeamMemoryConflictResolvedPayload,
    TeamMemoryConflictResolvedEvent,
    # TODO: Add imports for Team Cleanup events and payloads when implemented
)
from agents.infrastructure_crew.schemas.context_schemas import TeamMemoryInfo # For future use with TeamMemory
from .memory_manager import MemoryManager # MemoryEventType from here is no longer needed by TMM directly

# Local TeamMemoryEventType enum is removed.
# We will use StandardTeamMemoryEventType from schemas.

class TeamMemoryManager:
    """
    Manages memory allocation and sharing between teams.
    
    The TeamMemoryManager provides centralized memory management for different
    teams within the infrastructure crew, handling memory allocation, sharing,
    and conflict resolution.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the TeamMemoryManager.
        
        Args:
            config: Configuration dictionary for the manager
        
        Configuration Example:
        {
            "redis_url": "redis://localhost:6379/0",
            "default_quota": 0.1,
            "high_priority_quota": 0.2,
            "low_priority_quota": 0.05,
            "monitor_interval": 1,
            "sharing_policy": "round_robin"
        }
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._teams: Dict[str, TeamMemory] = {}
        self._lock = asyncio.Lock()
        self._metrics: Dict[str, Any] = {
            "total_allocated": 0,
            "active_teams": 0,
            "conflicts_resolved": 0,
            "sharing_attempts": 0,
            "sharing_success": 0
        }
        
        # Initialize sharing policy
        self._sharing_policy = self.config.get("sharing_policy", "round_robin")
        self._monitor_interval = self.config.get("monitor_interval", 1)
        
        # Initialize monitoring
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Initialize team memory quotas
        self._team_quotas = {
            "default": config.get("default_quota", 0.1),  # 10% of total memory
            "high_priority": config.get("high_priority_quota", 0.2),
            "low_priority": config.get("low_priority_quota", 0.05)
        }
        
        # Initialize memory sharing policies
        self._sharing_policies = {
            "default": "round_robin",
            "high_priority": "priority_based",
            "low_priority": "fair_share"
        }
        
        # Initialize Redis client
        self._redis = Redis.from_url(self.config.get("redis_url", "redis://localhost:6379/0"))
        
        # Initialize memory manager
        self._memory_manager = MemoryManager(config)

    async def _distribute_team_event(self, event: BaseEvent) -> None:
        """
        Distribute team-memory-related events via Redis.
        
        Args:
            event: The fully formed event object (e.g., TeamMemoryAllocationSuccessEvent).
        """
        # Event object is already created and typed.
        # It includes event_id, event_type, timestamp, source_entity_id, target_entity_id, payload, and priority.
        channel = f"team_memory_events:{event.event_type}:{event.target_entity_id if hasattr(event, 'target_entity_id') and event.target_entity_id else 'global'}"
        if hasattr(event, 'payload') and event.payload:
            await self._redis.publish(channel, event.model_dump_json())
            self.logger.debug(f"Published team event to Redis channel {channel}: {event.event_id} for target {getattr(event, 'target_entity_id', 'N/A')}")
        else:
            # Handle events that might not have a payload in the same way, or log warning
            # For now, assuming all distributed events will have a payload for model_dump_json()
            await self._redis.publish(channel, event.model_dump_json()) 
            self.logger.debug(f"Published team event (potentially w/o explicit payload) to Redis channel {channel}: {event.event_id}")

    async def create_team(self, team_name: str, priority: str = "default") -> str:
        """
        Create a new team with memory allocation.
        
        Args:
            team_name: Name of the team
            priority: Priority level for memory allocation
        
        Returns:
            Team ID
        """
        team_id = f"team_{team_name}_{str(uuid.uuid4())[:8]}"
        quota = self._team_quotas.get(priority, self._team_quotas["default"])
        
        team_memory = TeamMemory(
            team_id=team_id,
            team_name=team_name, # Add team_name
            quota_percentage=quota,
            priority=priority
            # last_updated uses default_factory from Pydantic model
        )
        
        await self._redis.hset("teams", team_id, json.dumps(team_memory.to_redis_dict()))
        self._teams[team_id] = team_memory
        self._metrics["active_teams"] += 1

        # Calculate quota_bytes for the event payload
        try:
            memory_stats = self._memory_manager.get_memory_usage() # This is synchronous
            total_system_memory = memory_stats.total_bytes
            calculated_quota_bytes = int(quota * total_system_memory)
        except Exception as e:
            self.logger.error(f"Failed to get total system memory or calculate quota_bytes for team {team_id}: {e}", exc_info=True)
            # Fallback or decide how to handle event if this fails. For now, log and use a placeholder or skip event.
            calculated_quota_bytes = 0 # Or some other sensible default/error indicator if event must be sent

        # Emit TeamMemoryAllocationSuccessEvent
        allocation_payload = TeamMemoryAllocationSuccessPayload(
            team_id=team_id,
            allocated_bytes=calculated_quota_bytes, # Assuming full quota is 'allocated' at creation
            quota_bytes=calculated_quota_bytes,
            priority=priority
            # timestamp is handled by Pydantic default_factory
        )
        allocation_event = TeamMemoryAllocationSuccessEvent(
            payload=allocation_payload,
            source_entity_id="TeamMemoryManager",
            target_entity_id=team_id,
            priority=EventPriority.MEDIUM # Default priority for this event type
        )
        await self._distribute_team_event(allocation_event)
        self.logger.info(f"Team {team_id} ('{team_name}') created with quota {team_memory.quota_percentage*100}%, {calculated_quota_bytes} bytes. Event emitted.")
        
        return team_id

    async def initialize(self):
        """
        Initialize team memory monitoring and load existing team data from Redis.
        """
        try:
            # Verify Redis connection
            if not await self._redis.ping():
                raise ConnectionError("Redis connection failed")
            
            # Load existing teams from Redis
            raw_team_data_map = await self._redis.hgetall("teams")
            for team_id_bytes, raw_data_bytes in raw_team_data_map.items():
                team_id_str = team_id_bytes.decode()
                raw_data_str = raw_data_bytes.decode()
                try:
                    team_data_dict = json.loads(raw_data_str)
                    if not isinstance(team_data_dict, dict):
                        self.logger.error(f"Parsed data for team {team_id_str} is not a dictionary: {team_data_dict}")
                        continue
                    self._teams[team_id_str] = TeamMemory.from_redis_dict(team_data_dict)
                    self.logger.info(f"Loaded team {team_id_str} from Redis.")
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON for team {team_id_str} from Redis: {raw_data_str}. Error: {e}")
                except Exception as e:
                    self.logger.error(f"Failed to load team {team_id_str} from Redis dict {raw_data_str if 'raw_data_str' in locals() else 'N/A'}: {e}", exc_info=True)
            self._metrics["active_teams"] = len(self._teams)

        except ConnectionError as e:
            self.logger.error(f"Redis connection failed during initialization: {e}")
            # Depending on policy, might re-raise or try to operate without Redis (limited functionality)
            raise RuntimeError(f"Failed to initialize Redis: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Error during TeamMemoryManager initialization: {e}", exc_info=True)
            # Decide if this is a fatal error for the manager
            raise RuntimeError(f"Failed to initialize TeamMemoryManager: {str(e)}") from e
        
        if self._monitor_task is None and not self._shutdown:
            self._monitor_task = asyncio.create_task(self._monitor_team_memory())
    
    async def _monitor_team_memory(self):
        """
        Monitor memory usage across teams and handle conflicts.
        """
        while not self._shutdown:
            try:
                # Placeholder for getting overall system memory usage if needed for context
                # current_system_usage = self._memory_manager.get_memory_usage()
                
                # Check for memory conflicts based on allocated quotas
                # Note: Actual per-team usage vs. quota check would require TeamMemory to track usage
                # or a mechanism to query it, which is not currently in place.
                # The existing _is_conflict logic is also a placeholder (always returns False).
                
                conflicting_pairs = self._detect_memory_conflicts()
                if conflicting_pairs:
                    self.logger.info(f"Detected {len(conflicting_pairs)} potential memory conflicts: {conflicting_pairs}")
                    conflict_payload = TeamMemoryConflictDetectedPayload(
                        conflicting_team_pairs=conflicting_pairs,
                        detection_timestamp=time.time() # Using time.time() for now, consider datetime
                    )
                    conflict_event = TeamMemoryConflictDetectedEvent(
                        payload=conflict_payload,
                        source_entity_id="TeamMemoryManagerMonitor",
                        priority=EventPriority.HIGH
                    )
                    await self._distribute_team_event(conflict_event)
                    
                    await self._resolve_conflicts(conflicting_pairs)
                
                await asyncio.sleep(self._monitor_interval)
                
            except asyncio.CancelledError:
                self.logger.info("Team memory monitoring task cancelled.")
                break
            except Exception as e:
                self.logger.error(f"Error in team memory monitoring loop: {e}", exc_info=True)
                # Avoid busy-looping on persistent errors
                await asyncio.sleep(self._monitor_interval * 5)
    
    def _detect_memory_conflicts(self) -> List[Tuple[str, str]]:
        """
        Detect memory conflicts between teams.
        
        Returns:
            List of conflicting team pairs
        """
        conflicts = []
        for team_id, team_data in self._teams.items():
            for other_id, other_data in self._teams.items():
                if team_id != other_id:
                    if self._is_conflict(team_data, other_data):
                        conflicts.append((team_id, other_id))
        return conflicts
    
    def _is_conflict(self, team1: TeamMemory, team2: TeamMemory) -> bool:
        """
        Check if two teams are in conflict.
        
        Args:
            team1: First team's data
            team2: Second team's data
            
        Returns:
            True if teams are in conflict, False otherwise
        """
        # Implement conflict detection logic, e.g., based on overlapping resource claims if TeamMemory tracked specific resources.
        # For now, if _is_conflict is based on simple quota percentages, it might not be meaningful
        # as quotas are managed not to exceed 100% of total system memory in sum through other logic.
        # This placeholder assumes conflicts are more complex, e.g. if teams request specific, limited resources.
        # If it were just about total quota, `_is_conflict` might check if sum of quotas > 1.0, but that's a system-wide check.
        # For pairwise conflict, it's more nuanced. For now, returning False as per original.
        # Example of a hypothetical check (not for current model):
        # if team1.requested_specific_resource_X and team2.requested_specific_resource_X:
        #     return True 
        return False
    
    async def _resolve_conflicts(self, conflicts: List[Tuple[str, str]]) -> None:
        """
        Attempt to resolve memory conflicts between teams.
        Actual resolution logic is currently a placeholder.
        
        Args:
            conflicts: List of conflicting team pairs (e.g., [("team_A_id", "team_B_id")])
        """
        async with self._lock:
            for team1_id, team2_id in conflicts:
                resolution_details = "Conflict resolution strategy not yet implemented."
                resolution_status = "NO_ACTION_TAKEN"
                self.logger.warning(f"Attempting to resolve conflict between {team1_id} and {team2_id}: {resolution_details}")
                
                # Placeholder for actual conflict resolution logic
                # This logic would modify team quotas or states and update Redis.
                # For now, we just log and emit an event.
                
                try:
                    # Example: In a real scenario, you might adjust quotas:
                    # team1_data = self._teams.get(team1_id)
                    # team2_data = self._teams.get(team2_id)
                    # if team1_data and team2_data:
                    #     # Apply some policy, e.g., reduce lower priority team's quota
                    #     pass # Actual changes and Redis updates would go here
                    
                    resolved_payload = TeamMemoryConflictResolvedPayload(
                        conflicting_team_pair=(team1_id, team2_id),
                        resolution_strategy_applied="placeholder_no_action",
                        outcome_description=resolution_details,
                        status=resolution_status, # e.g., "RESOLVED_ADJUSTED_QUOTAS", "FAILED_INSUFFICIENT_INFO"
                        timestamp=time.time() # Consider datetime
                    )
                    resolved_event = TeamMemoryConflictResolvedEvent(
                        payload=resolved_payload,
                        source_entity_id="TeamMemoryManagerResolver",
                        target_entity_id=f"{team1_id},{team2_id}", # Or a general channel
                        priority=EventPriority.MEDIUM
                    )
                    await self._distribute_team_event(resolved_event)
                    self._metrics["conflicts_resolved"] = self._metrics.get("conflicts_resolved", 0) + 1
                    
                except Exception as e:
                    self.logger.error(
                        f"Error during placeholder conflict resolution for {team1_id} and {team2_id}: {e}",
                        exc_info=True
                    )
                    # Optionally emit a resolution_failed event here
    
    async def allocate_memory(self, team_id: str, quota_percentage: float, priority: str = "default", requested_by: Optional[str] = None) -> bool:
        """
        Allocate memory quota to a team.
        
        Args:
            team_id: Unique identifier for the team
            quota_percentage: Memory quota as a fraction of total memory (e.g., 0.1 for 10%)
            priority: Priority level of the team ("high", "default", "low")
            requested_by: Optional identifier of the entity requesting allocation.
            
        Returns:
            True if allocation was successful, False otherwise
        """
        requested_bytes_val = 0
        try:
            memory_stats = self._memory_manager.get_memory_usage()
            total_system_memory = memory_stats.total_bytes
            requested_bytes_val = int(quota_percentage * total_system_memory)
        except Exception as e:
            self.logger.error(f"Failed to get total system memory for allocation request for team {team_id}: {e}", exc_info=True)
            # If we can't determine total memory, we can't accurately reflect requested_bytes. 
            # Depending on policy, we might fail here or proceed with requested_bytes_val = 0 for the event.

        request_payload = TeamMemoryAllocationRequestPayload(
            team_id=team_id,
            requested_bytes=requested_bytes_val,
            priority=priority,
            requested_by=requested_by
        )
        request_event = TeamMemoryAllocationRequestEvent(
            payload=request_payload,
            source_entity_id=requested_by if requested_by else "TeamMemoryManager",
            target_entity_id=team_id,
            priority=EventPriority.HIGH
        )
        await self._distribute_team_event(request_event)

        async with self._lock:
            if team_id in self._teams:
                self.logger.warning(f"Team {team_id} already has allocated memory. Allocation failed.")
                failure_payload = TeamMemoryAllocationFailurePayload(
                    team_id=team_id,
                    requested_bytes=requested_bytes_val,
                    reason=f"Team {team_id} already exists.",
                    priority=priority
                )
                failure_event = TeamMemoryAllocationFailureEvent(
                    payload=failure_payload,
                    source_entity_id="TeamMemoryManager",
                    target_entity_id=team_id,
                    priority=EventPriority.MEDIUM
                )
                await self._distribute_team_event(failure_event)
                return False
            
            team_memory = TeamMemory(
                id=team_id,
                quota=quota_percentage, # Storing percentage quota in TeamMemory object
                priority=priority,
                last_updated=time.time()
            )
            
            # TODO: Original `if not await self._resolve_conflicts(team_memory):` was problematic as `_resolve_conflicts` expects List[Tuple[str, str]].
            # Conflict resolution logic needs to be reviewed and correctly integrated before allocation or handled by monitoring.
            # For now, allocation proceeds. A pre-allocation conflict check might be needed here.

            self._teams[team_id] = team_memory
            await self._redis.hset("teams", team_id, team_memory.to_dict()) # Persist to Redis
            self._metrics["total_allocated"] += quota_percentage # Metric tracks percentage sum
            self._metrics["active_teams"] += 1

            success_payload = TeamMemoryAllocationSuccessPayload(
                team_id=team_id,
                allocated_bytes=requested_bytes_val, # Actual bytes allocated
                quota_bytes=requested_bytes_val, # Quota in bytes
                priority=priority
            )
            success_event = TeamMemoryAllocationSuccessEvent(
                payload=success_payload,
                source_entity_id="TeamMemoryManager",
                target_entity_id=team_id,
                priority=EventPriority.MEDIUM
            )
            await self._distribute_team_event(success_event)
            
            self.logger.info(f"Allocated {quota_percentage:.2%} ({requested_bytes_val} bytes) memory to team {team_id}")
            return True
    
    async def deallocate_memory(self, team_id: str, requested_by: Optional[str] = None) -> bool:
        """
        Deallocate memory quota from a team.
        
        Args:
            team_id: Unique identifier for the team
            requested_by: Optional identifier of the entity requesting deallocation.
            
        Returns:
            True if deallocation was successful, False otherwise
        """
        request_payload = TeamMemoryDeallocationRequestPayload(
            team_id=team_id,
            requested_by=requested_by
        )
        request_event = TeamMemoryDeallocationRequestEvent(
            payload=request_payload,
            source_entity_id=requested_by if requested_by else "TeamMemoryManager",
            target_entity_id=team_id,
            priority=EventPriority.HIGH
        )
        await self._distribute_team_event(request_event)

        async with self._lock:
            if team_id not in self._teams:
                self.logger.warning(f"Team {team_id} does not have allocated memory. Deallocation failed.")
                # Optionally, emit a TeamMemoryDeallocationFailureEvent if defined and appropriate.
                return False
            
            team_memory_obj = self._teams[team_id]
            deallocated_quota_percentage = team_memory_obj.quota
            
            deallocated_bytes_val = 0
            try:
                memory_stats = self._memory_manager.get_memory_usage()
                total_system_memory = memory_stats.total_bytes
                deallocated_bytes_val = int(deallocated_quota_percentage * total_system_memory)
            except Exception as e:
                self.logger.error(f"Failed to get total system memory for deallocation calculation for team {team_id}: {e}", exc_info=True)
                # If this fails, deallocated_bytes_val will remain 0 for the event, which is not ideal but better than crashing.

            del self._teams[team_id]
            await self._redis.hdel("teams", team_id) # Remove from Redis as well

            self._metrics["total_allocated"] -= deallocated_quota_percentage # Metric tracks percentage sum
            self._metrics["active_teams"] -= 1
            
            success_payload = TeamMemoryDeallocationSuccessPayload(
                team_id=team_id,
                deallocated_bytes=deallocated_bytes_val,
                remaining_quota_bytes=0 # Team is removed, so its quota is 0
            )
            success_event = TeamMemoryDeallocationSuccessEvent(
                payload=success_payload,
                source_entity_id="TeamMemoryManager",
                target_entity_id=team_id,
                priority=EventPriority.MEDIUM
            )
            await self._distribute_team_event(success_event)
            
            self.logger.info(f"Deallocated memory from team {team_id} (was {deallocated_quota_percentage:.2%}, {deallocated_bytes_val} bytes). Event emitted.")
            return True
    
    async def share_memory(self, source_team_id: str, target_team_id: str, amount_percentage: float, requested_by: Optional[str] = None) -> bool:
        """
        Share memory quota (as a percentage of total system memory) between teams.
        
        Args:
            source_team_id: The ID of the team sharing memory.
            target_team_id: The ID of the team receiving memory.
            amount_percentage: Percentage of total system memory to share (e.g., 0.05 for 5%).
            requested_by: Optional identifier of the entity requesting the share.

        Returns:
            True if sharing was successful, False otherwise.
        """
        bytes_to_share_val = 0
        try:
            memory_stats = self._memory_manager.get_memory_usage()
            total_system_memory = memory_stats.total_bytes
            bytes_to_share_val = int(amount_percentage * total_system_memory)
        except Exception as e:
            self.logger.error(f"Failed to get total system memory for sharing request from {source_team_id} to {target_team_id}: {e}", exc_info=True)
            # Proceed with bytes_to_share_val = 0 for initiated event, failure will likely follow

        initiated_payload = TeamMemorySharingInitiatedPayload(
            source_team_id=source_team_id,
            target_team_id=target_team_id,
            bytes_to_share=bytes_to_share_val,
            requested_by=requested_by
        )
        initiated_event = TeamMemorySharingInitiatedEvent(
            payload=initiated_payload,
            source_entity_id=requested_by if requested_by else "TeamMemoryManager",
            # Target could be ambiguous; perhaps source_team_id or a general channel
            target_entity_id=source_team_id, 
            priority=EventPriority.MEDIUM
        )
        await self._distribute_team_event(initiated_event)

        async with self._lock:
            source_data = self._teams.get(source_team_id)
            if not source_data:
                reason = f"Source team {source_team_id} not found."
                self.logger.warning(f"Memory sharing failed: {reason}")
                await self._emit_sharing_failed_event(source_team_id, target_team_id, bytes_to_share_val, reason, requested_by)
                return False

            # Check if source team has enough quota (percentage based)
            if source_data.quota_percentage < amount_percentage:
                reason = f"Source team {source_team_id} has insufficient quota ({source_data.quota:.2%}) to share {amount_percentage:.2%}."
                self.logger.warning(f"Memory sharing failed: {reason}")
                await self._emit_sharing_failed_event(source_team_id, target_team_id, bytes_to_share_val, reason, requested_by)
                return False
            
            target_data = self._teams.get(target_team_id)
            if not target_data:
                # If target team doesn't exist, create it with default priority and the shared amount as its initial quota.
                # Check if team already exists
                if target_team_id in self._teams:
                    # Update existing team's quota and priority
                    target_data = self._teams[target_team_id]
                    target_data.quota_percentage += amount_percentage
                    target_data.last_updated = datetime.now(timezone.utc) # Update timestamp
                    self.logger.info(f"Updated team {target_team_id} quota to {target_data.quota_percentage*100}%")
                else:
                    # Create new team entry
                    target_data = TeamMemory(
                        team_id=target_team_id,
                        team_name=target_team_id, # Use team_id as name if not provided
                        quota_percentage=amount_percentage,
                        priority="default"
                        # last_updated uses default_factory
                    )
                    self._teams[target_team_id] = target_data
                    self._metrics["active_teams"] += 1
                    self.logger.info(f"Allocated new team {target_team_id} with quota {amount_percentage*100}%")

            # Update quotas (percentage based)
            source_data.quota_percentage -= amount_percentage
            source_data.last_updated = datetime.now(timezone.utc)

            # Persist changes to Redis
            await self._redis.hset("teams", source_team_id, json.dumps(source_data.to_redis_dict()))
            await self._redis.hset("teams", target_team_id, json.dumps(target_data.to_redis_dict()))

            completed_payload = TeamMemorySharingCompletedPayload(
                source_team_id=source_team_id,
                target_team_id=target_team_id,
                bytes_shared=bytes_to_share_val,
                source_team_new_quota_bytes=int(source_data.quota_percentage * total_system_memory),
                target_team_new_quota_bytes=int(target_data.quota_percentage * total_system_memory)
            )
            completed_event = TeamMemorySharingCompletedEvent(
                payload=completed_payload,
                source_entity_id="TeamMemoryManager",
                target_entity_id=target_team_id, # Or source_team_id, or both via separate events/channel
                priority=EventPriority.MEDIUM
            )
            await self._distribute_team_event(completed_event)
            
            self.logger.info(f"Successfully shared {amount_percentage:.2%} ({bytes_to_share_val} bytes) memory from {source_team_id} to {target_team_id}.")
            return True

    async def _emit_sharing_failed_event(self, source_team_id: str, target_team_id: str, bytes_to_share: int, reason: str, requested_by: Optional[str]):
        failed_payload = TeamMemorySharingFailedPayload(
            source_team_id=source_team_id,
            target_team_id=target_team_id,
            bytes_to_share=bytes_to_share,
            reason=reason
        )
        failed_event = TeamMemorySharingFailedEvent(
            payload=failed_payload,
            source_entity_id=requested_by if requested_by else "TeamMemoryManager",
            target_entity_id=source_team_id,
            priority=EventPriority.WARNING
        )
        await self._distribute_team_event(failed_event)
    

    
    async def get_team_memory_usage(self, team_id: str) -> Dict[str, Any]:
        """
        Get memory usage statistics for a team.
        
        Args:
            team_id: The team ID
            
        Returns:
            Dictionary of memory usage statistics
        """
        team_data = self._teams.get(team_id)
        
        if team_data:
            return {
                "usage": team_data.quota_percentage,
                "quota": team_data.quota_percentage,
                "priority": team_data.priority,
                "timestamp": team_data.last_updated
            }
        else:
            return {}
    
    async def get_system_memory_usage(self) -> Dict[str, Any]:
        """
        Get overall system memory usage statistics.
        
        Returns:
            Dictionary of system memory usage statistics
        """
        return self._memory_manager.get_memory_usage()
    
    async def shutdown(self):
        """
        Shutdown the team memory manager.
        """
        self._shutdown = True
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Clean up team allocations
        async with self._lock:
            for team_id in list(self._teams.keys()):
                await self.deallocate_memory(team_id)
        
        self.logger.info("TeamMemoryManager shutdown complete")
