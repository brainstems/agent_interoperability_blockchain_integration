from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

class ReputationRating(BaseModel):
    """
    Represents a single rating event submitted for an agent after completing a task.
    """
    rating_id: UUID = Field(default_factory=uuid4, description="Unique identifier for the rating.")
    rater_agent_id: str = Field(..., description="ID of the agent submitting the rating (e.g., TaskOrchestrationAgent).")
    rated_agent_id: str = Field(..., description="ID of the agent being rated (e.g., a WorkerAgent).")
    task_id: str = Field(..., description="The ID of the Contract Net Protocol task this rating pertains to.")
    score: float = Field(..., ge=0.0, le=5.0, description="Numerical score, e.g., on a scale of 0.0 to 5.0.")
    comment: Optional[str] = Field(None, description="Optional textual comment or feedback.")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the rating was submitted.")

class AgentReputation(BaseModel):
    """
    Represents the aggregated reputation score for an agent.
    """
    agent_id: str = Field(..., description="ID of the agent whose reputation this is.")
    average_score: float = Field(0.0, description="The average score calculated from all ratings.")
    number_of_ratings: int = Field(0, description="Total number of ratings received by the agent.")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when this reputation summary was last updated.")

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "worker_agent_001",
                "average_score": 4.5,
                "number_of_ratings": 10,
                "last_updated": "2024-05-26T12:00:00Z"
            }
        }
