import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    PENDING = "PENDING"  # Initial state, or if dependencies not met
    READY = "READY"  # All dependencies met, ready for processing or bidding
    CFP_ISSUED = "CFP_ISSUED"  # Call for Proposals issued, awaiting bids
    EVALUATING_BIDS = "EVALUATING_BIDS"  # Bidding period ended, evaluating bids
    AWARDED = "AWARDED"  # Task awarded to a worker, awaiting worker to start
    IN_PROGRESS = "IN_PROGRESS"  # Worker has accepted and started the task
    COMPLETED = "COMPLETED"  # Task completed successfully
    FAILED = "FAILED"  # Task execution failed, or bidding process failed critically
    CANCELLED = "CANCELLED"  # Task cancelled by user or system
    BIDDING_FAILED = "BIDDING_FAILED" # Bidding process failed (e.g. no suitable bids)

class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class TaskDefinition(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = Field(default_factory=list) # Changed from List[uuid.UUID]
    data: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_to: Optional[str] = None # Worker agent_id
    deadline_seconds: Optional[int] = None # Expected duration/timeout for the task
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    result_data: Optional[Any] = None # Stores the actual result from the worker
    error_message: Optional[str] = None
    requires_bidding: bool = Field(True, description="Indicates if the task should go through the Contract Net Protocol for bidding.")

    class Config:
        use_enum_values = True # Ensures enum values are used in serialization

class TaskUpdateRequest(BaseModel):
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assigned_to: Optional[str] = None
    result: Optional[Any] = None
    error_message: Optional[str] = None
    # updated_at will be handled by the updating logic

class TaskSubmissionRequest(BaseModel):
    name: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: List[str] = Field(default_factory=list) # Changed from List[uuid.UUID]
    data: Optional[Dict[str, Any]] = None
    # Add a flag to indicate if task should go through bidding
    requires_bidding: bool = Field(True, description="Set to False to bypass Contract Net and dispatch directly if possible.")
