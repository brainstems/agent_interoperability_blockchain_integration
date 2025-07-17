from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

class KGEntity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str = Field(..., description="The type of the knowledge graph entity.")
    name: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    related_entities: List[Dict[str, Union[str, Dict[str, Any]]]] = Field(default_factory=list, description="List of related entities with relationship type and properties")
    # Example for related_entities entry: 
    # { "target_id": "uuid_of_target", "relationship_type": "HAS_TASK", "properties": { "status": "active" } }

class Project(KGEntity):
    entity_type: str = "Project"
    status: Optional[str] = None # e.g., "planning", "active", "completed", "on_hold"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = None
    owner_id: Optional[str] = None # ID of the agent or user owning the project
    repository_url: Optional[str] = None
    current_milestone: Optional[str] = None
    project_manager_id: Optional[str] = None # ID of the agent managing the project

class Task(KGEntity):
    entity_type: str = "Task"
    project_id: Optional[str] = None # ID of the project this task belongs to
    assignee_id: Optional[str] = None # ID of the agent or user assigned to the task
    status: Optional[str] = None # e.g., "todo", "in_progress", "blocked", "done"
    priority: Optional[int] = Field(default=0) # e.g., 0 (low) to 3 (high)
    due_date: Optional[datetime] = None
    dependencies: List[str] = Field(default_factory=list) # List of Task IDs this task depends on

class Product(KGEntity):
    entity_type: str = "Product"
    version: Optional[str] = None
    release_date: Optional[datetime] = None
    features: List[str] = Field(default_factory=list)

class MarketSignal(KGEntity):
    entity_type: str = "MarketSignal"
    source: Optional[str] = None # e.g., "twitter", "news_article", "competitor_announcement"
    signal_strength: Optional[float] = Field(default=0.0) # e.g., 0.0 to 1.0
    sentiment: Optional[str] = None # e.g., "positive", "negative", "neutral"
    target_product_ids: List[str] = Field(default_factory=list)

class PerformanceMetric(KGEntity):
    entity_type: str = "PerformanceMetric"
    metric_name: str
    value: Union[float, str, bool]
    unit: Optional[str] = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    target_entity_id: Optional[str] = None # ID of the entity this metric pertains to (e.g., Project, Product, Task)
    target_entity_type: Optional[str] = None

class Decision(KGEntity):
    entity_type: str = "Decision"
    decided_by_id: Optional[str] = None # Agent or User ID
    rationale: Optional[str] = None
    inputs: List[Dict[str, Any]] = Field(default_factory=list) # e.g., list of MarketSignal IDs, PerformanceMetric IDs used
    impact_level: Optional[int] = Field(default=0) # e.g., 0 (low) to 3 (high)

class Outcome(KGEntity):
    entity_type: str = "Outcome"
    decision_id: Optional[str] = None # ID of the Decision that led to this outcome
    achieved_at: Optional[datetime] = None
    success_level: Optional[str] = None # e.g., "high_success", "moderate_success", "failure"
    learnings: Optional[str] = None

class KGRelationship(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    target_id: str
    relationship_type: str # e.g., "HAS_TASK", "DEPENDS_ON", "GENERATED_BY", "LED_TO"
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentSchema(KGEntity):
    entity_type: str = "Agent"
    # Agent-specific characteristics
    reputation: Optional[Union[float, str]] = None # Score or link/description
    shared_memory_info: Optional[str] = None # Link or description
    communication_protocol_info: Optional[str] = None
    common_goal_info: Optional[str] = None
    skills_description: Optional[str] = None # Could be a list of skill URIs/names in the future
    is_self_organizing: Optional[bool] = None
    autonomy_level_description: Optional[str] = None
    continuous_learning_enabled: Optional[bool] = None
    adaptation_capability_description: Optional[str] = None
    resilience_mechanisms_description: Optional[str] = None
    fault_tolerance_description: Optional[str] = None
    transparent_incentives_info: Optional[str] = None # Link or description
    governance_model_info: Optional[str] = None # Link or description
    is_interoperable: Optional[bool] = None
    interoperability_description: Optional[str] = None
    is_composable: Optional[bool] = None
    composability_description: Optional[str] = None
    member_of_crews: List[str] = Field(default_factory=list) # List of AgentCrew IDs

class AgentCrewSchema(KGEntity):
    entity_type: str = "AgentCrew"
    # Crew-specific characteristics (many can be inherited or aggregated from agents)
    # Or they can have their own distinct values at the crew level
    reputation: Optional[Union[float, str]] = None
    shared_memory_info: Optional[str] = None
    communication_protocol_info: Optional[str] = None
    common_goal: str # Crew must have a common goal
    skill_diversity_description: Optional[str] = None
    is_self_organizing: Optional[bool] = None
    autonomy_level_description: Optional[str] = None
    continuous_learning_enabled: Optional[bool] = None # For the crew as a unit
    adaptation_capability_description: Optional[str] = None # For the crew as a unit
    resilience_mechanisms_description: Optional[str] = None
    fault_tolerance_description: Optional[str] = None
    transparent_incentives_info: Optional[str] = None
    governance_model_info: Optional[str] = None
    is_interoperable: Optional[bool] = None # As a crew unit
    interoperability_description: Optional[str] = None
    is_composable: Optional[bool] = None # As a crew unit
    composability_description: Optional[str] = None
    has_members: List[str] = Field(default_factory=list) # List of Agent IDs

