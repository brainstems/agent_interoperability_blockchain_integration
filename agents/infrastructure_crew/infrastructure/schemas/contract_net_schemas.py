from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import uuid
import time

# --- Redis Channel/Queue Definitions ---
CONTRACT_NET_NAMESPACE = "contract_net"
# General CFP channel, workers subscribe to this or category-specific ones
CFP_BROADCAST_CHANNEL = f"{CONTRACT_NET_NAMESPACE}:cfp:broadcast"
# Pattern for category-specific CFP channels if needed
CFP_CATEGORY_CHANNEL_PATTERN = lambda category: f"{CONTRACT_NET_NAMESPACE}:cfp:{category}"
# Pattern for queue where bids for a specific task_id are submitted
BID_SUBMISSION_QUEUE_PATTERN = lambda task_id: f"{CONTRACT_NET_NAMESPACE}:bids:{task_id}"
# Pattern for queue where a worker receives award notifications (can be worker's main input queue or dedicated)
AWARD_NOTIFICATION_QUEUE_PATTERN = lambda worker_id: f"workers:{worker_id}:awards"
# Pattern for queue where results for a specific task_id are submitted
TASK_RESULT_QUEUE_PATTERN = lambda task_id: f"{CONTRACT_NET_NAMESPACE}:results:{task_id}"


class CFPMessage(BaseModel):
    """Call For Proposals message published by the TaskOrchestrationAgent."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for the task and this CFP instance.")
    task_type: str = Field(..., description="Category or type of the task, e.g., 'image_analysis', 'text_translation'.")
    task_description: Dict[str, Any] = Field(..., description="Detailed description of the task requirements.")
    input_data_reference: Optional[str] = Field(None, description="Reference to input data, e.g., 'redis_key:task_data_123', S3 URI.")
    evaluation_criteria: List[tuple[str, str]] = Field(
        default_factory=list,
        description="How bids will be judged. List of tuples: (field_name_in_bid_details, sort_order ('asc'/'desc')). E.g., [('completion_time_estimate_hours', 'asc'), ('cost_bid_units', 'asc')]"
    )
    bid_submission_deadline_ts: float = Field(..., description="Unix timestamp by which bids must be submitted.")
    bid_submission_queue: str = Field(..., description="Full Redis key (list) where bidders should submit their bids.")
    # Optional fields for market mechanisms integration
    max_budget: Optional[float] = Field(None, description="Maximum budget allocated for this task, if applicable.")
    requester_id: Optional[str] = Field(None, description="ID of the agent/crew requesting the task, for budget deduction or context.")
    publication_timestamp: float = Field(default_factory=time.time)

class BidMessage(BaseModel):
    """Bid message submitted by a worker/swarm in response to a CFP."""
    task_id: str = Field(..., description="The task_id from the CFP this bid is for.")
    bidder_id: str = Field(..., description="Unique ID of the worker/swarm submitting the bid.")
    bidder_capabilities: List[str] = Field(default_factory=list, description="List of capabilities the bidder possesses relevant to the task.")
    bid_details: Dict[str, Any] = Field(..., description="Flexible dictionary containing bid specifics, e.g., {'completion_time_estimate_hours': 2, 'cost_bid_units': 10, 'confidence_score': 0.95}. Must contain fields mentioned in CFP's evaluation_criteria.")
    award_notification_queue: str = Field(..., description="The Redis queue where this bidder expects to receive an award notification if they win.")
    submission_timestamp: float = Field(default_factory=time.time)

class AwardMessage(BaseModel):
    """Award message sent by TaskOrchestrationAgent to the winning bidder."""
    task_id: str = Field(..., description="The task_id that has been awarded.")
    winning_bidder_id: str = Field(..., description="ID of the worker/swarm that won the bid.")
    status: str = Field("awarded", description="Status of the award.")
    task_details: Dict[str, Any] = Field(..., description="Full task details, potentially richer than the original CFP, for the winner to execute.")
    input_data_reference: Optional[str] = Field(None, description="Reference to input data for the task.")
    result_submission_queue: str = Field(..., description="The Redis queue where the winner should submit their task results.")
    # Optional fields for market mechanisms integration
    agreed_cost: Optional[float] = Field(None, description="The cost agreed upon for task completion, if applicable.")
    award_timestamp: float = Field(default_factory=time.time)

class TaskResultMessage(BaseModel):
    """Message sent by the worker upon task completion or failure."""
    task_id: str = Field(..., description="The task_id this result pertains to.")
    worker_id: str = Field(..., description="ID of the worker submitting the result.")
    success: bool = Field(..., description="True if the task was completed successfully, False otherwise.")
    status: str = Field(..., description="Overall status of the task, e.g., 'completed_successfully', 'failed'. Use 'success' field for boolean outcome.")
    result_data: Optional[Any] = Field(None, description="The actual result data of the task, if applicable.")
    output_data_reference: Optional[str] = Field(None, description="Reference to the output data if stored elsewhere, e.g., 'redis_key:result_data_123'.")
    result_details: Optional[Dict[str, Any]] = Field(None, description="Additional structured results or metadata.")
    error_message: Optional[str] = Field(None, description="Error message if the task failed.")
    completion_timestamp: float = Field(default_factory=time.time)
