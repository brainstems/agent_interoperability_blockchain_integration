from pydantic import BaseModel, Field, validator, HttpUrl
from typing import Dict, Any, Optional, Union, List
from enum import Enum
import uuid
from datetime import datetime, timezone
from typing_extensions import Literal

class EventPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4()}")
    event_type: str # e.g., "user.created", "service.heartbeat_missed"
    source_entity_id: Optional[str] = None # Preferred: ID of the agent, service, crew, or system component that originated the event
    target_entity_id: Optional[str] = None # Optional: ID of the entity this event is directed to
    source_service_id: Optional[str] = None # Legacy/Specific: ID of the service that originated the event. Consider using source_entity_id.
    source_crew_id: Optional[str] = None # Legacy/Specific: ID of the crew that originated the event. Consider using source_entity_id.
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0.0"
    priority: EventPriority = EventPriority.MEDIUM
    payload: Dict[str, Any] = Field(default_factory=dict) # Specific event classes should override this with a typed Pydantic model
    correlation_id: Optional[str] = None # For tracking related events
    # schema_id: Optional[str] = None # Could point to a registered schema for the payload

    @validator('timestamp', pre=True, always=True)
    def set_timestamp_utc(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        if v is None:
            return datetime.now(timezone.utc)
        return v

class CriticalEventPayload(BaseModel):
    affected_service_id: Optional[str] = None
    affected_crew_id: Optional[str] = None
    severity: int = Field(default=1, ge=1, le=5) # 1 (low) to 5 (high)
    message: str
    details: Optional[Dict[str, Any]] = None

class CriticalEvent(BaseEvent):
    event_type: str = "system.critical_alert"
    priority: EventPriority = EventPriority.CRITICAL
    payload: CriticalEventPayload

class DataChangeEventPayload(BaseModel):
    entity_type: str # e.g., "customer_profile", "product_inventory"
    entity_id: Union[str, int]
    change_type: str # e.g., "created", "updated", "deleted"
    changed_fields: Optional[Dict[str, Any]] = None # For 'updated', old_value: new_value
    full_entity_snapshot: Optional[Dict[str, Any]] = None # Optional: include the full new state

class DataChangeEvent(BaseEvent):
    event_type: str = "data.changed"
    priority: EventPriority = EventPriority.MEDIUM # Or HIGH depending on sensitivity
    payload: DataChangeEventPayload

class ServiceStatusChangeEventPayload(BaseModel):
    service_id: str
    old_status: Optional[str] = None # Could use ServiceStatus enum if available here
    new_status: str # Could use ServiceStatus enum
    reason: Optional[str] = None

class ServiceStatusChangeEvent(BaseEvent):
    event_type: str = "service.status_changed"
    priority: EventPriority = EventPriority.HIGH
    payload: ServiceStatusChangeEventPayload

# --- Service Registration & Discovery ---

class EndpointType(str, Enum):
    HTTP = "http"
    GRPC = "grpc"
    WEBSOCKET = "websocket"
    INTERNAL_QUEUE = "internal_queue"

class ServiceEndpoint(BaseModel):
    """Represents a network endpoint where a service can be accessed."""
    type: EndpointType
    url: str
    methods: Optional[List[str]] = None  # e.g., ["GET", "POST"] for HTTP
    description: Optional[str] = None
    is_secure: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ServiceStatus(str, Enum):
    STARTING = "STARTING"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    OFFLINE = "OFFLINE"

class ServiceInfo(BaseModel):
    """Comprehensive information about a registered service."""
    service_id: str = Field(..., description="Unique identifier for the service")
    name: str = Field(..., description="Human-readable name of the service")
    version: str = Field(..., description="Service version (semver recommended)")
    description: Optional[str] = None
    status: ServiceStatus = ServiceStatus.STARTING
    endpoints: List[ServiceEndpoint] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list, description="List of capabilities/features provided by this service")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the service")
    last_heartbeat: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @validator('endpoints', each_item=True)
    def validate_endpoints(cls, v):
        # Example validation: Ensure HTTP URLs start with http:// or https://
        if v.type == EndpointType.HTTP and not v.url.startswith(('http://', 'https://')):
            raise ValueError("HTTP/HTTPS URLs must start with 'http://' or 'https://'")
        return v

class ServiceRegistrationRequest(ServiceInfo):
    """Used when a service registers itself with the registry.
    
    Inherits all fields from ServiceInfo and adds registration-specific fields.
    """
    # Override to make these fields required for registration
    service_id: str = Field(..., description="Unique identifier for the service")
    name: str = Field(..., description="Human-readable name of the service")
    
    # Additional fields specific to registration
    ttl_seconds: int = Field(
        default=30,
        description="Time-to-live in seconds before the registration expires without a heartbeat"
    )
    
    # Override the default to ensure we always get the current time at registration
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_schema_extra = {
            "example": {
                "service_id": "user-service-1",
                "name": "User Service",
                "version": "1.0.0",
                "description": "Handles user authentication and profile management",
                "status": "STARTING",
                "endpoints": [
                    {
                        "type": "http",
                        "url": "http://localhost:8000/api/v1",
                        "methods": ["GET", "POST", "PUT", "DELETE"],
                        "is_secure": False
                    }
                ],
                "capabilities": ["authentication", "user_management"],
                "ttl_seconds": 30
            }
        }

class ServiceHeartbeat(ServiceInfo):
    """Sent by services to indicate they are still alive."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: Optional[Dict[str, Any]] = None
    status: ServiceStatus = ServiceStatus.HEALTHY
    
    class Config:
        # Exclude the heartbeat timestamp from the service info when updating
        exclude = {"timestamp"}

# --- System Health & Monitoring Events ---

class SystemOverallHealthPayload(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    overall_status: str # e.g., "healthy", "warning", "critical"
    active_services: int
    total_events_processed: int
    error_rate_percentage: float = Field(default=0.0)
    avg_processing_time_ms: float = Field(default=0.0)
    redis_connection_status: str # e.g., "connected", "disconnected"
    memory_usage_mb: float # System or relevant process memory usage
    cpu_utilization_percentage: Optional[float] = None # System or relevant process CPU usage
    detailed_metrics: Optional[Dict[str, Any]] = None # For CrewManager.get_metrics() or similar

class SystemHealthBroadcastEvent(BaseEvent):
    event_type: str = "system.health.broadcast"
    priority: EventPriority = EventPriority.MEDIUM
    payload: SystemOverallHealthPayload

class ResourceAlertType(str, Enum):
    CPU_HIGH = "cpu_high"
    MEMORY_HIGH = "memory_high"
    DISK_SPACE_LOW = "disk_space_low"
    REDIS_UNAVAILABLE = "redis_unavailable"
    NETWORK_LATENCY_HIGH = "network_latency_high"

class ResourceAlertPayload(BaseModel):
    alert_type: ResourceAlertType
    resource_id: Optional[str] = None # e.g., specific server, pod, or 'system_redis'
    current_value: Union[float, str]
    threshold_value: Optional[Union[float, str]] = None
    message: str
    severity: int = Field(default=3, ge=1, le=5) # 1 (low) to 5 (critical)

class ResourceAlertEvent(BaseEvent):
    event_type: str = "system.resource.alert"
    priority: EventPriority = EventPriority.HIGH # Alerts are typically high priority
    payload: ResourceAlertPayload

class ServicePerformanceWarningPayload(BaseModel):
    service_id: str
    service_name: Optional[str] = None
    metric_name: str # e.g., "error_rate", "avg_latency_ms", "heartbeat_miss_rate"
    current_value: float
    threshold_value: float
    observation_period_seconds: Optional[int] = None
    message: str

class ServicePerformanceWarningEvent(BaseEvent):
    event_type: str = "service.performance.warning"
    priority: EventPriority = EventPriority.HIGH
    payload: ServicePerformanceWarningPayload


# --- Memory Management Events ---

class MemoryEventType(str, Enum):
    """Enumeration of memory event types from MemoryManager."""
    USAGE = "memory.usage"
    PRESSURE = "memory.pressure"
    CLEANUP_TRIGGERED = "memory.cleanup.triggered"
    CLEANUP_COMPLETED = "memory.cleanup.completed"
    EVICTION = "memory.eviction"

class MemoryPressureLevel(str, Enum):
    """Enumeration of memory pressure levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class MemoryUsageStatsPayload(BaseModel):
    """Detailed memory usage statistics."""
    total_bytes: int
    available_bytes: int
    used_bytes: int
    free_bytes: int # Often same as available, but good to have if system distinguishes
    usage_percentage: float = Field(..., ge=0, le=100)

class MemoryUsageEventPayload(BaseModel):
    """Payload for memory usage events."""
    stats: MemoryUsageStatsPayload
    pressure_level: MemoryPressureLevel
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MemoryUsageEvent(BaseEvent):
    event_type: Literal[MemoryEventType.USAGE] = MemoryEventType.USAGE
    payload: MemoryUsageEventPayload

class MemoryPressureEventPayload(BaseModel):
    """Payload for memory pressure events."""
    pressure_level: MemoryPressureLevel
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MemoryPressureEvent(BaseEvent):
    event_type: Literal[MemoryEventType.PRESSURE] = MemoryEventType.PRESSURE
    payload: MemoryPressureEventPayload
    priority: EventPriority = EventPriority.HIGH # Pressure events are usually important

class MemoryCleanupTriggeredEventPayload(BaseModel):
    """Payload for memory cleanup triggered events."""
    strategy_used: Optional[str] = None
    target_reduction_bytes: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MemoryCleanupTriggeredEvent(BaseEvent):
    event_type: Literal[MemoryEventType.CLEANUP_TRIGGERED] = MemoryEventType.CLEANUP_TRIGGERED
    payload: MemoryCleanupTriggeredEventPayload

class MemoryCleanupCompletedEventPayload(BaseModel):
    """Payload for memory cleanup completed events."""
    bytes_freed: int
    duration_seconds: float
    strategies_applied: List[str] = Field(default_factory=list)
    errors_encountered: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MemoryCleanupCompletedEvent(BaseEvent):
    event_type: Literal[MemoryEventType.CLEANUP_COMPLETED] = MemoryEventType.CLEANUP_COMPLETED
    payload: MemoryCleanupCompletedEventPayload

class MemoryEvictionEventPayload(BaseModel):
    """Payload for memory eviction events."""
    evicted_item_ids: List[str]
    bytes_freed: int
    reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MemoryEvictionEvent(BaseEvent):
    event_type: Literal[MemoryEventType.EVICTION] = MemoryEventType.EVICTION
    payload: MemoryEvictionEventPayload
    priority: EventPriority = EventPriority.HIGH

# --- Team Memory Management Events ---

class TeamMemoryEventType(str, Enum):
    """Enumeration of team memory event types from TeamMemoryManager."""
    ALLOCATION_REQUEST = "team.memory.allocation.request"
    ALLOCATION_SUCCESS = "team.memory.allocation.success"
    ALLOCATION_FAILURE = "team.memory.allocation.failure"
    DEALLOCATION_REQUEST = "team.memory.deallocation.request"
    DEALLOCATION_SUCCESS = "team.memory.deallocation.success"
    QUOTA_UPDATED = "team.memory.quota.updated"
    SHARING_INITIATED = "team.memory.sharing.initiated"
    SHARING_COMPLETED = "team.memory.sharing.completed"
    CONFLICT_DETECTED = "team.memory.conflict.detected"
    CONFLICT_RESOLVED = "team.memory.conflict.resolved"
    TEAM_CLEANUP_TRIGGERED = "team.memory.cleanup.triggered"
    TEAM_CLEANUP_COMPLETED = "team.memory.cleanup.completed"

class TeamMemoryAllocationRequestPayload(BaseModel):
    team_id: str
    requested_bytes: int
    priority: Optional[str] = None # e.g., low, medium, high, critical
    purpose: Optional[str] = None

class TeamMemoryAllocationRequestEvent(BaseEvent):
    event_type: Literal[TeamMemoryEventType.ALLOCATION_REQUEST] = TeamMemoryEventType.ALLOCATION_REQUEST
    payload: TeamMemoryAllocationRequestPayload

class TeamMemoryAllocationSuccessPayload(BaseModel):
    team_id: str
    allocated_bytes: int
    new_quota_bytes: int
    current_usage_bytes: int

class TeamMemoryAllocationSuccessEvent(BaseEvent):
    event_type: Literal[TeamMemoryEventType.ALLOCATION_SUCCESS] = TeamMemoryEventType.ALLOCATION_SUCCESS
    payload: TeamMemoryAllocationSuccessPayload

class TeamMemoryAllocationFailurePayload(BaseModel):
    team_id: str
    requested_bytes: int
    reason: str
    available_bytes: Optional[int] = None

class TeamMemoryAllocationFailureEvent(BaseEvent):
    event_type: Literal[TeamMemoryEventType.ALLOCATION_FAILURE] = TeamMemoryEventType.ALLOCATION_FAILURE
    payload: TeamMemoryAllocationFailurePayload
    priority: EventPriority = EventPriority.HIGH

class TeamMemoryDeallocationRequestPayload(BaseModel):
    team_id: str
    bytes_to_deallocate: int

class TeamMemoryDeallocationRequestEvent(BaseEvent):
    event_type: Literal[TeamMemoryEventType.DEALLOCATION_REQUEST] = TeamMemoryEventType.DEALLOCATION_REQUEST
    payload: TeamMemoryDeallocationRequestPayload

class TeamMemoryDeallocationSuccessPayload(BaseModel):
    team_id: str
    deallocated_bytes: int
    new_quota_bytes: int

class TeamMemoryDeallocationSuccessEvent(BaseEvent):
    event_type: Literal[TeamMemoryEventType.DEALLOCATION_SUCCESS] = TeamMemoryEventType.DEALLOCATION_SUCCESS
    payload: TeamMemoryDeallocationSuccessPayload

class TeamMemoryQuotaUpdatedPayload(BaseModel):
    team_id: str
    old_quota_bytes: int
    new_quota_bytes: int
    reason: Optional[str] = None # e.g., 'manual_adjustment', 'system_rebalance'

class TeamMemoryQuotaUpdatedEvent(BaseEvent):
    event_type: Literal[TeamMemoryEventType.QUOTA_UPDATED] = TeamMemoryEventType.QUOTA_UPDATED
    payload: TeamMemoryQuotaUpdatedPayload

# Add more TeamMemory event payloads and classes as needed (Sharing, Conflict, Cleanup)
