"""
Team Memory Model (Pydantic-based)

This module contains the TeamMemory Pydantic model used by TeamMemoryManager.
It's designed to be compatible with Redis storage and align with broader context schemas.
"""

from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class TeamMemory(BaseModel):
    """Represents memory allocation and state for a team using Pydantic."""
    team_id: str = Field(description="Unique identifier for the team.")
    team_name: Optional[str] = Field(None, description="Human-readable name for the team.")
    # Storing quota as a percentage (e.g., 0.1 for 10%) as TeamMemoryManager logic uses this.
    quota_percentage: float = Field(description="Allocated memory quota for the team as a percentage of total system memory.")
    # current_usage_bytes would be ideal but TMM doesn't track this per team object directly yet.
    current_usage_percentage: float = Field(default=0.0, description="Current memory usage by the team as a percentage of its quota or total system memory. Placeholder.")
    priority: str = Field(default="default", description="Priority level of the team (e.g., low, default, high).")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of the last update to this team's memory state.")
    shared_context_ids: List[str] = Field(default_factory=list, description="List of IDs of generic context objects shared by/with this team.")
    # metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata for the team memory entry.")

    class Config:
        # populate_by_name = True # Allows using 'id' and 'quota' during initialization if needed for old data, maps to team_id, quota_percentage
        json_encoders = {
            datetime: lambda v: v.isoformat() # Ensure datetime is ISO string in JSON
        }
        json_schema_extra = {
            "example": {
                "team_id": "crew_alpha_processing_team_123",
                "team_name": "Alpha Processing Crew",
                "quota_percentage": 0.15, # 15%
                "current_usage_percentage": 0.05,
                "priority": "high",
                "last_updated": "2024-05-28T12:00:00Z",
                "shared_context_ids": ["ctx_shared_db_config_abc"]
            }
        }

    # The to_dict method is no longer needed; use model_dump() and model_dump_json().
    # For Redis HSET/HMSET, model_dump() can be used, but ensure datetime is serialized to string/timestamp.
    # Pydantic's model_dump() by default (mode='python') keeps datetime as datetime objects.
    # To store in Redis hash, we need to convert them.

    def to_redis_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format suitable for Redis HMSET, serializing datetime.
           Pydantic's model_dump(mode='json') serializes the whole thing to a JSON string.
           model_dump() gives a dict but datetime objects are still datetime. 
        """
        data = self.model_dump(exclude_none=True) # exclude_none=True can save space
        if 'last_updated' in data and isinstance(data['last_updated'], datetime):
            data['last_updated'] = data['last_updated'].isoformat()
        # shared_context_ids is a list, Redis hash fields are strings. Convert list to JSON string.
        if 'shared_context_ids' in data and isinstance(data['shared_context_ids'], list):
            import json
            data['shared_context_ids'] = json.dumps(data['shared_context_ids'])
        return data

    @classmethod
    def from_redis_dict(cls, data: Dict[str, Any]) -> "TeamMemory":
        """Create a TeamMemory instance from a dictionary retrieved from Redis.
           Handles deserialization of specific fields like datetime and JSON strings.
        """
        if 'last_updated' in data and isinstance(data['last_updated'], (str, bytes)):
            try:
                # Redis might return bytes, ensure it's a string for isoformat parsing
                str_val = data['last_updated'].decode() if isinstance(data['last_updated'], bytes) else data['last_updated']
                data['last_updated'] = datetime.fromisoformat(str_val.replace('Z', '+00:00'))
            except ValueError as e:
                # Fallback for potential float timestamps from old system
                try:
                    float_val = float(str_val)
                    data['last_updated'] = datetime.fromtimestamp(float_val, tz=timezone.utc)
                except ValueError:
                    raise ValueError(f"Could not parse last_updated: {data['last_updated']} - {e}") from e
        
        if 'shared_context_ids' in data and isinstance(data['shared_context_ids'], (str, bytes)):
            import json
            try:
                str_val = data['shared_context_ids'].decode() if isinstance(data['shared_context_ids'], bytes) else data['shared_context_ids']
                data['shared_context_ids'] = json.loads(str_val)
            except json.JSONDecodeError as e:
                # Handle cases where it might not be a valid JSON string (e.g. empty or malformed)
                # Depending on requirements, could default to empty list or raise error
                data['shared_context_ids'] = [] 
                # Consider logging a warning here

        # Map old field names if necessary, though direct usage of new names is preferred.
        # If 'id' is in data and 'team_id' is not, map it.
        if 'id' in data and 'team_id' not in data:
            data['team_id'] = data.pop('id')
        if 'quota' in data and 'quota_percentage' not in data:
            data['quota_percentage'] = data.pop('quota')

        return cls.model_validate(data)
