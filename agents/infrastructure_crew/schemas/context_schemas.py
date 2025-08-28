from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List, Union, Literal
import uuid
from datetime import datetime, timezone

class TeamMemoryInfo(BaseModel):
    """Detailed information about a team's memory allocation and usage."""
    team_id: str = Field(..., description="Unique identifier for the team.")
    team_name: Optional[str] = Field(None, description="Human-readable name for the team.")
    quota_bytes: int = Field(..., description="Allocated memory quota for the team in bytes.")
    current_usage_bytes: int = Field(default=0, description="Current memory usage by the team in bytes.")
    priority: str = Field(default="medium", description="Priority level of the team (e.g., low, medium, high).")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of the last update to this memory info.")
    shared_context_ids: List[str] = Field(default_factory=list, description="List of IDs of generic context objects shared by/with this team.")

    class Config:
        json_schema_extra = {
            "example": {
                "team_id": "crew_alpha_processing_team",
                "team_name": "Alpha Processing Crew",
                "quota_bytes": 1073741824, # 1 GB
                "current_usage_bytes": 536870912, # 512 MB
                "priority": "high",
                "last_updated": "2024-05-26T10:00:00Z",
                "shared_context_ids": ["ctx_shared_config_123", "ctx_intermediate_result_456"]
            }
        }

class GenericContextObject(BaseModel):
    """A generic container for shared data or context across agents and crews."""
    context_id: str = Field(default_factory=lambda: f"ctx_{uuid.uuid4()}", description="Unique identifier for the context object.")
    context_type: str = Field(..., description="Type of the context (e.g., 'shared_config', 'intermediate_result', 'knowledge_snippet').")
    version: int = Field(default=1, description="Version of the context object data.")
    owner_entity_id: str = Field(..., description="ID of the agent or crew that owns/created this context.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(None, description="Optional expiration timestamp for the context.")
    access_control: Optional[Dict[str, List[str]]] = Field(None, description="Access control rules, e.g., {'read': ['crew_A', 'agent_X']}")
    # data: BaseModel  # Ideal, but makes it less 'generic'. Start with Dict or specific common models.
    data_payload: Dict[str, Any] = Field(..., description="The actual data payload of the context object.")
    data_schema_identifier: Optional[str] = Field(None, description="Identifier (e.g., URI or name) of the schema validating the data_payload, if any.")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata like tags, source, relevance score.")

    @validator('last_modified_at', pre=True, always=True)
    def update_last_modified_at(cls, v, values):
        return values.get('created_at') # On creation, last_modified_at is same as created_at
        # For actual updates, this would need to be set explicitly by the updating logic.

    class Config:
        json_schema_extra = {
            "example": {
                "context_id": "ctx_user_preferences_abc",
                "context_type": "user_preferences_set",
                "version": 2,
                "owner_entity_id": "agent_ui_interaction_handler_01",
                "created_at": "2024-05-25T14:30:00Z",
                "last_modified_at": "2024-05-26T09:15:00Z",
                "expires_at": "2024-06-26T09:15:00Z",
                "access_control": {"read": ["crew_personalization", "agent_recommendation_engine_02"]},
                "data_payload": {"theme": "dark", "notifications_enabled": True, "language": "en-US"},
                "data_schema_identifier": "UserPreferencesV2",
                "metadata": {"source": "user_settings_panel", "tags": ["ui", "preferences"]}
            }
        }

class EntityState(BaseModel):
    """Represents the operational state of an agent or a crew."""
    entity_id: str = Field(..., description="Unique identifier for the agent or crew.")
    entity_type: Literal['agent', 'crew'] = Field(..., description="Type of the entity.")
    status: str = Field(..., description="Current operational status (e.g., 'IDLE', 'ACTIVE', 'ERROR', 'INITIALIZING').")
    current_task_id: Optional[str] = Field(None, description="ID of the task the entity is currently processing, if any.")
    capabilities: List[str] = Field(default_factory=list, description="List of capabilities this entity possesses.")
    health_metrics: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Key-value pairs of health metrics (e.g., 'cpu_load', 'avg_response_time').")
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of the last heartbeat received from this entity.")
    custom_state_data: Optional[Dict[str, Any]] = Field(None, description="Agent/crew-specific structured state data.")
    state_schema_identifier: Optional[str] = Field(None, description="Identifier for the schema of custom_state_data, if applicable.")

    class Config:
        json_schema_extra = {
            "example": {
                "entity_id": "worker_agent_data_processor_007",
                "entity_type": "agent",
                "status": "ACTIVE_PROCESSING_BATCH_XYZ",
                "current_task_id": "task_batch_xyz_part_3",
                "capabilities": ["data_validation", "image_resizing", "report_generation"],
                "health_metrics": {"avg_processing_time_ms": 150, "error_rate_percentage": 0.5, "queue_length": 10},
                "last_heartbeat": "2024-05-26T10:05:00Z",
                "custom_state_data": {"current_batch_size": 1000, "processed_items_in_batch": 345},
                "state_schema_identifier": "DataProcessorAgentStateV1"
            }
        }

