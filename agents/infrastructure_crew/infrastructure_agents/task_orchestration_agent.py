import asyncio
import uuid
import functools
from abc import ABC, abstractmethod
import logging
import json
import time # Added for timestamps
from pydantic import BaseModel, Field, ValidationError # Keep for TaskDefinition compatibility if needed elsewhere
from datetime import datetime # Keep for TaskDefinition compatibility if needed elsewhere
from typing import Dict, List, Optional, Any, cast

from redis.asyncio import Redis as AsyncRedis
from ...common.base_agent import BaseAgent, AgentConfig
from .registry_manager_agent import RegistryManagerAgent # For reputation system
from ..schemas.reputation_schemas import ReputationRating # For reputation system
from ..schemas.task_schemas import (
    TaskDefinition,
    TaskStatus,
    TaskPriority,
    TaskUpdateRequest,
    TaskSubmissionRequest
)
from ...infrastructure.schemas.contract_net_schemas import (
    CFPMessage,
    BidMessage,
    AwardMessage,
    TaskResultMessage,
    CONTRACT_NET_NAMESPACE,
    CFP_BROADCAST_CHANNEL,
    BID_SUBMISSION_QUEUE_PATTERN,
    AWARD_NOTIFICATION_QUEUE_PATTERN, # May not be directly used by TOA for sending, but good to have
    TASK_RESULT_QUEUE_PATTERN
)

logger = logging.getLogger(__name__)

class TaskOrchestrationAgentConfig(AgentConfig):
    default_bidding_duration_seconds: int = 300 # e.g., 5 minutes
    default_task_execution_timeout_seconds: int = 3600 # e.g., 1 hour
    non_biddable_tasks_channel: str = "tasks:direct_dispatch" # For tasks not requiring bidding

class TaskOrchestrationAgent(BaseAgent, ABC):
    def __init__(self, agent_id: str, config: Optional[TaskOrchestrationAgentConfig] = None, registry_manager: Optional['RegistryManagerAgent'] = None):
        super().__init__(agent_id, config or TaskOrchestrationAgentConfig(agent_id=agent_id)) # Pass agent_id to config if it uses it
        self.redis_pool: Optional[AsyncRedis] = None # Will be initialized in _initialize
        self.config: TaskOrchestrationAgentConfig = cast(TaskOrchestrationAgentConfig, self.config) # Ensure correct type
        self.registry_manager = registry_manager
        self.is_running = False # Added to manage agent's active state
        
        # Stores all tasks managed by this agent, including those in bidding
        self.tasks: Dict[str, TaskDefinition] = {} # Changed key to str for consistency with task_id from CFPMessage
        
        # Contract Net Protocol specific state
        self.active_cfps: Dict[str, CFPMessage] = {} # task_id -> CFPMessage
        # Stores asyncio.Task objects for background processes
        self.cfp_bid_collection_tasks: Dict[str, asyncio.Task] = {} # task_id -> asyncio.Task for bid collection
        self.task_result_listeners: Dict[str, asyncio.Task] = {} # task_id -> asyncio.Task for result listening
        
        # Ensure default_task_deadline_seconds is available
        self.default_task_deadline_seconds = self.config.default_task_execution_timeout_seconds # Or some other default

    async def _initialize(self) -> None:
        """Initialize agent resources, like the Redis connection.
           Called by BaseAgent's startup sequence.
        """
        logger.info(f"[{self.agent_id}] Initializing TaskOrchestrationAgent (_initialize)...")
        try:
            await self._connect_redis() # _connect_redis should handle setting self.redis_pool
            if not self.redis_pool:
                logger.error(f"[{self.agent_id}] Failed to connect to Redis during initialization.")
                # BaseAgent.initialize will set self.initialized based on whether an exception occurs
                # So, if redis_pool is not set, we should raise an error or ensure self.initialized remains False
                # For now, logging error. BaseAgent's initialize will complete, but agent might not be functional.
                # Consider raising an exception here to halt initialization if Redis is critical.
                raise ConnectionError(f"[{self.agent_id}] Failed to connect to Redis.")
            logger.info(f"[{self.agent_id}] TaskOrchestrationAgent initialized successfully (_initialize).")
        except Exception as e:
            logger.error(f"[{self.agent_id}] Exception during _initialize: {e}", exc_info=True)
            raise # Re-raise exception so BaseAgent.initialize knows it failed

    async def _process(self):
        """Main processing loop for the agent.
           Called by BaseAgent's startup sequence after _initialize.
        """
        logger.info(f"[{self.agent_id}] TaskOrchestrationAgent processing loop (_process) started.")
        try:
            while self.is_running: # is_running should be managed by BaseAgent's start/stop
                # logger.debug(f"[{self.agent_id}] TOA alive tick.")
                await asyncio.sleep(5)  # Keep alive, yield control
        except asyncio.CancelledError:
            logger.info(f"[{self.agent_id}] Processing loop (_process) cancelled.")
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error in processing loop (_process): {e}", exc_info=True)
        finally:
            logger.info(f"[{self.agent_id}] Processing loop (_process) stopped.")

    async def initialize(self) -> None:
        # This method is effectively overridden by BaseAgent's initialize, which calls _initialize.
        # Keeping it for conceptual clarity or if direct calls were intended, but ensuring signature match.
        logger.info(f"[{self.agent_id}] TaskOrchestrationAgent initialize method called (delegating to BaseAgent).")
        await super().initialize() # Call BaseAgent's initialize which in turn calls self._initialize

    async def start(self):
        if not self.initialized:
            logger.info(f"[{self.agent_id}] Agent not initialized. Attempting to initialize now.")
            await self.initialize() # This calls BaseAgent's initialize, which calls _initialize
        
        if not self.initialized:
            logger.error(f"[{self.agent_id}] Initialization failed. Cannot start agent.")
            return

        self.is_running = True
        logger.info(f"[{self.agent_id}] TaskOrchestrationAgent started and is_running set to True.")
        # Start the main processing loop if it's defined and uses self.is_running
        # For example, if _process is meant to be the main loop:
        # asyncio.create_task(self._process()) # If _process is the main loop

    async def submit_task(self, submission_request: TaskSubmissionRequest) -> TaskDefinition:
        task_id_str = str(uuid.uuid4()) # Ensure task_id is string
        new_task = TaskDefinition(
            task_id=task_id_str,
            name=submission_request.name,
            description=submission_request.description,
            priority=submission_request.priority,
            dependencies=submission_request.dependencies,
            data=submission_request.data,
            status=TaskStatus.PENDING, # Initial status
            requires_bidding=submission_request.requires_bidding
        )
        self.tasks[task_id_str] = new_task
        logger.info(f"[{self.agent_id}] Submitted new task: {task_id_str} - {new_task.name}, Requires Bidding: {new_task.requires_bidding}")
        # Check dependencies and process readiness (this might be more complex in a real system)
        if not new_task.dependencies: # Simplified: if no deps, consider ready
            new_task.status = TaskStatus.READY
            new_task.updated_at = datetime.utcnow()
            self.tasks[task_id_str] = new_task # Update task in store
            await self._process_task_readiness(new_task)
        return new_task

    async def get_task(self, task_id: str) -> Optional[TaskDefinition]: # Changed task_id type to str
        task = self.tasks.get(task_id)
        if task:
            logger.debug(f"[{self.agent_id}] Retrieved task: {task_id}")
        else:
            logger.warning(f"[{self.agent_id}] Task not found: {task_id}")
        return task

    async def update_task(self, task_id: str, update_request: TaskUpdateRequest) -> Optional[TaskDefinition]: # Changed task_id type to str
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"[{self.agent_id}] Cannot update. Task not found: {task_id}")
            return None

        update_data = update_request.dict(exclude_unset=True)
        original_status = task.status

        if not update_data:
            logger.info(f"[{self.agent_id}] No update data provided for task: {task_id}")
            return task # Return current task if no updates

        updated_task = task.copy(update=update_data)
        updated_task.updated_at = datetime.utcnow()
        self.tasks[task_id] = updated_task
        logger.info(f"[{self.agent_id}] Updated task: {task_id}. Changes: {update_data}")

        # If task status changed to READY, process its readiness
        if 'status' in update_data and updated_task.status == TaskStatus.READY and original_status != TaskStatus.READY:
            await self._process_task_readiness(updated_task)
        elif updated_task.status == TaskStatus.CANCELLED and task_id in self.active_cfps:
            # If a task is cancelled while CFP is active, try to cancel bidding process
            await self._cancel_cfp_process(task_id, "Task cancelled by update")

        return updated_task

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        assigned_to: Optional[str] = None
    ) -> List[TaskDefinition]:
        logger.debug(f"[{self.agent_id}] Listing tasks with filters - Status: {status}, Priority: {priority}, AssignedTo: {assigned_to}")
        filtered_tasks = []
        for task in self.tasks.values():
            if status and task.status != status:
                continue
            if priority and task.priority != priority:
                continue
            if assigned_to and task.assigned_to != assigned_to:
                continue
            filtered_tasks.append(task)
        
        logger.info(f"[{self.agent_id}] Found {len(filtered_tasks)} tasks matching criteria.")
        return filtered_tasks

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "initialized": self.initialized,
            "total_tasks": len(self.tasks),
            "tasks_by_status": {s.value: sum(1 for t in self.tasks.values() if t.status == s) for s in TaskStatus}
        }

    async def _process_task_readiness(self, task: TaskDefinition):
        if task.status != TaskStatus.READY:
            logger.debug(f"[{self.agent_id}] Task {task.task_id} is not READY, current status: {task.status}. Not processing for dispatch/bidding.")
            return

        if not self.redis_pool:
            logger.error(f"[{self.agent_id}] Redis pool not available. Cannot process task {task.task_id}.")
            return

        if task.requires_bidding:
            logger.info(f"[{self.agent_id}] Task {task.task_id} requires bidding. Initiating CFP process.")
            await self._initiate_cfp(task)
        else:
            logger.info(f"[{self.agent_id}] Task {task.task_id} does not require bidding. Dispatching directly.")
            await self._direct_dispatch_task(task)

    async def _initiate_cfp(self, task: TaskDefinition):
        if task.task_id in self.active_cfps:
            logger.warning(f"[{self.agent_id}] CFP already active for task {task.task_id}. Ignoring duplicate initiation.")
            return

        if not self.redis_pool:
            logger.error(f"[{self.agent_id}] Redis pool not available. Cannot initiate CFP for task {task.task_id}.")
            task.status = TaskStatus.FAILED # Or PENDING for retry
            task.error_message = "Redis pool unavailable for CFP initiation"
            self.tasks[task.task_id] = task
            return

        bid_submission_queue = BID_SUBMISSION_QUEUE_PATTERN(task.task_id)
        cfp_message = CFPMessage(
            task_id=task.task_id,
            task_type=task.name, # Using task.name as a proxy for task_type for now
            task_description=task.data or {"details": task.description or "N/A"},
            input_data_reference=task.data.get("input_ref") if task.data else None,
            evaluation_criteria=[("cost_bid_units", "asc"), ("completion_time_estimate_hours", "asc")], # Example criteria
            bid_submission_deadline_ts=time.time() + self.config.default_bidding_duration_seconds,
            bid_submission_queue=bid_submission_queue,
            requester_id=self.agent_id
        )

        try:
            await self.redis_pool.publish(CFP_BROADCAST_CHANNEL, cfp_message.json())
            task.status = TaskStatus.CFP_ISSUED
            task.updated_at = datetime.utcnow()
            self.tasks[task.task_id] = task
            self.active_cfps[task.task_id] = cfp_message
            logger.info(f"[{self.agent_id}] Published CFP for task {task.task_id} to {CFP_BROADCAST_CHANNEL}. Bids to {bid_submission_queue}.")

            # Schedule bid collection and evaluation
            bid_collection_task = asyncio.create_task(self._schedule_bid_collection(task.task_id, cfp_message.bid_submission_deadline_ts))
            self.cfp_bid_collection_tasks[task.task_id] = bid_collection_task
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error initiating CFP for task {task.task_id}: {e}", exc_info=True)
            task.status = TaskStatus.FAILED
            task.error_message = f"CFP initiation failed: {e}"
            self.tasks[task.task_id] = task

    async def _schedule_bid_collection(self, task_id: str, deadline_ts: float):
        delay = max(0, deadline_ts - time.time())
        logger.info(f"[{self.agent_id}] Scheduling bid collection for task {task_id} in {delay:.2f} seconds.")
        await asyncio.sleep(delay)
        if task_id in self.active_cfps: # Check if CFP is still active (not cancelled)
            logger.info(f"[{self.agent_id}] Bid submission deadline reached for task {task_id}. Collecting bids.")
            await self._collect_and_evaluate_bids(task_id)
        else:
            logger.info(f"[{self.agent_id}] Bid collection for task {task_id} was cancelled or already processed.")

    async def _collect_and_evaluate_bids(self, task_id: str):
        task = self.tasks.get(task_id)
        cfp_message = self.active_cfps.get(task_id)

        if not task or not cfp_message:
            logger.warning(f"[{self.agent_id}] Task {task_id} or CFP not found during bid collection. Aborting.")
            if task_id in self.active_cfps: del self.active_cfps[task_id]
            if task_id in self.cfp_bid_collection_tasks: del self.cfp_bid_collection_tasks[task_id]
            if task and task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.status = TaskStatus.FAILED
                task.error_message = "Internal error during bid collection setup."
                self.tasks[task_id] = task
            return

        logger.info(f"[{self.agent_id}] Collecting bids for task {task_id} from {cfp_message.bid_submission_queue}.")
        task.status = TaskStatus.EVALUATING_BIDS
        task.updated_at = datetime.utcnow()
        self.tasks[task_id] = task

        if not self.redis_pool:
            logger.error(f"[{self.agent_id}] Redis pool not available for bid collection of task {task_id}.")
            task.status = TaskStatus.FAILED
            task.error_message = "Redis unavailable during bid collection."
            self.tasks[task_id] = task
            if task_id in self.active_cfps: del self.active_cfps[task_id]
            if task_id in self.cfp_bid_collection_tasks: del self.cfp_bid_collection_tasks[task_id]
            return

        try:
            # Fetch all bids and remove the queue atomically if possible, or fetch then delete.
            # For simplicity, using LRANGE and DEL. In high-concurrency, consider Lua script or WATCH.
            bid_strings = await self.redis_pool.lrange(cfp_message.bid_submission_queue, 0, -1)
            await self.redis_pool.delete(cfp_message.bid_submission_queue)
            
            valid_bids: List[BidMessage] = []
            if not bid_strings:
                logger.warning(f"[{self.agent_id}] No bids received for task {task_id}.")
            else:
                logger.info(f"[{self.agent_id}] Received {len(bid_strings)} bid(s) for task {task_id}.")
                for i, bid_json_str in enumerate(bid_strings):
                    try:
                        bid_data = json.loads(bid_json_str)
                        # Ensure task_id in bid matches the current task_id
                        if bid_data.get("task_id") != task_id:
                            logger.warning(f"[{self.agent_id}] Bid {i+1} for task {task_id} has mismatched task_id: {bid_data.get('task_id')}. Discarding.")
                            continue
                        bid = BidMessage(**bid_data)
                        valid_bids.append(bid)
                    except json.JSONDecodeError as e:
                        logger.error(f"[{self.agent_id}] Error decoding bid JSON for task {task_id}, bid string: {bid_json_str}. Error: {e}")
                    except Exception as e: # Pydantic validation error etc.
                        logger.error(f"[{self.agent_id}] Error validating bid for task {task_id}, bid data: {bid_json_str}. Error: {e}")
            
            await self._evaluate_bids_and_award(task_id, valid_bids)

        except Exception as e:
            logger.error(f"[{self.agent_id}] Error during bid collection for task {task_id}: {e}", exc_info=True)
            task.status = TaskStatus.FAILED
            task.error_message = f"Bid collection failed: {e}"
            self.tasks[task_id] = task
            # Clean up CFP state as this path means evaluation won't happen
            if task_id in self.active_cfps:
                del self.active_cfps[task_id]
                # Added comment for clarity
            if task_id in self.cfp_bid_collection_tasks:
                del self.cfp_bid_collection_tasks[task_id]
                # Removed task_id from cfp_bid_collection_tasks

    def _apply_evaluation_criteria(self, bids: List[BidMessage], criteria: List[tuple[str, str]]) -> List[BidMessage]:
        """Sorts bids based on multiple criteria. Modifies the list in place if using sort, or returns new sorted list."""
        def compare_bids(bid1: BidMessage, bid2: BidMessage):
            for field, order in criteria:
                val1 = bid1.bid_details.get(field)
                val2 = bid2.bid_details.get(field)

                if val1 is None and val2 is None:
                    continue
                if val1 is None:
                    return 1 if order == 'asc' else -1
                if val2 is None:
                    return -1 if order == 'asc' else 1
                
                try:
                    if val1 < val2:
                        return -1 if order == 'asc' else 1
                    if val1 > val2:
                        return 1 if order == 'asc' else -1
                except TypeError:
                    logger.warning(f"Type error comparing {field}: {val1} ({type(val1)}) vs {val2} ({type(val2)})")
                    continue
            return 0

        return sorted(bids, key=functools.cmp_to_key(compare_bids))

    async def _evaluate_bids_and_award(self, task_id: str, bids: List[BidMessage]):
        task = self.tasks.get(task_id)
        cfp_message = self.active_cfps.get(task_id)

        if not task or not cfp_message:
            logger.warning(f"[{self.agent_id}] Task {task_id} or CFP not found during bid evaluation. Aborting.")
            if task_id in self.active_cfps:
                del self.active_cfps[task_id]
            if task_id in self.cfp_bid_collection_tasks:
                del self.cfp_bid_collection_tasks[task_id]
            if task and task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.status = TaskStatus.FAILED
                task.error_message = "Internal error during bid evaluation setup."
                self.tasks[task_id] = task
            return

        winning_bid: Optional[BidMessage] = None
        if not bids:
            logger.warning(f"[{self.agent_id}] No valid bids to evaluate for task {task_id}.")
        else:
            logger.info(f"[{self.agent_id}] Evaluating {len(bids)} bids for task {task_id} using criteria: {cfp_message.evaluation_criteria}")
            eval_criteria = cfp_message.evaluation_criteria
            if not eval_criteria and task.data and "evaluation_criteria" in task.data:
                eval_criteria = task.data["evaluation_criteria"]
            
            if not eval_criteria:
                 logger.warning(f"[{self.agent_id}] No evaluation criteria specified for task {task_id}. Selecting first valid bid if any.")
                 if bids: winning_bid = bids[0]
            else:
                sorted_bids = self._apply_evaluation_criteria(bids, eval_criteria)
                if sorted_bids:
                    winning_bid = sorted_bids[0]
                    logger.info(f"[{self.agent_id}] Winning bid for task {task_id} from bidder {winning_bid.bidder_id} with details: {winning_bid.bid_details}")
                else:
                    logger.warning(f"[{self.agent_id}] No suitable winning bid found for task {task_id} after applying criteria.")

        if winning_bid:
            task.status = TaskStatus.AWARDED
            task.assigned_to = winning_bid.bidder_id
            task.updated_at = datetime.utcnow()
            agreed_cost = winning_bid.bid_details.get("cost_bid_units")
            if agreed_cost is not None:
                if task.data is None:
                    task.data = {}
                task.data['agreed_cost'] = agreed_cost
            
            self.tasks[task_id] = task

            result_submission_queue = TASK_RESULT_QUEUE_PATTERN(task_id)
            award_message = AwardMessage(
                task_id=task_id,
                winning_bidder_id=winning_bid.bidder_id,
                task_details=cfp_message.task_description,
                input_data_reference=cfp_message.input_data_reference,
                result_submission_queue=result_submission_queue,
                agreed_cost=agreed_cost
            )
            try:
                if not self.redis_pool:
                    raise ConnectionError("Redis pool not available for publishing award.")
                
                award_queue = winning_bid.award_notification_queue 
                await self.redis_pool.rpush(award_queue, award_message.json())
                logger.info(f"[{self.agent_id}] Sent award notification for task {task_id} to bidder {winning_bid.bidder_id} on queue {award_queue}.")
                
                result_listener = asyncio.create_task(self._listen_for_task_results(task_id, result_submission_queue))
                self.task_result_listeners[task_id] = result_listener
            except Exception as e:
                logger.error(f"[{self.agent_id}] Failed to send award or start result listener for task {task_id}: {e}", exc_info=True)
                task.status = TaskStatus.FAILED
                task.error_message = f"Award dispatch failed: {e}"
                task.assigned_to = None
                if task.data and 'agreed_cost' in task.data:
                    del task.data['agreed_cost']
                self.tasks[task_id] = task
        else:
            logger.warning(f"[{self.agent_id}] Bidding failed for task {task_id} - no winning bid selected.")
            task.status = TaskStatus.BIDDING_FAILED
            task.error_message = "No suitable bids received or selected."
            task.updated_at = datetime.utcnow()
            self.tasks[task_id] = task

        if task_id in self.active_cfps:
            del self.active_cfps[task_id]
        if task_id in self.cfp_bid_collection_tasks:
            del self.cfp_bid_collection_tasks[task_id]
        logger.debug(f"[{self.agent_id}] Cleaned up CFP state for task {task_id}.")

    async def _direct_dispatch_task(self, task: TaskDefinition):
        if not self.redis_pool:
            logger.error(f"[{self.agent_id}] Redis pool not available. Cannot directly dispatch task {task.task_id}.")
            task.status = TaskStatus.FAILED # Or PENDING for retry
            task.error_message = "Redis pool unavailable for direct dispatch"
            self.tasks[task.task_id] = task
            return
        try:
            task_json = task.json()
            await self.redis_pool.publish(self.config.non_biddable_tasks_channel, task_json)
            # Task status remains READY, worker will update it to IN_PROGRESS upon pickup
            logger.info(f"[{self.agent_id}] Directly dispatched task {task.task_id} to {self.config.non_biddable_tasks_channel}")
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error directly dispatching task {task.task_id}: {e}", exc_info=True)
            task.status = TaskStatus.FAILED
            task.error_message = f"Direct dispatch failed: {e}"
            self.tasks[task.task_id] = task

    async def _cancel_cfp_process(self, task_id: str, reason: str):
        logger.info(f"[{self.agent_id}] Attempting to cancel CFP process for task {task_id} due to: {reason}")
        if task_id in self.cfp_bid_collection_tasks:
            self.cfp_bid_collection_tasks[task_id].cancel()
            del self.cfp_bid_collection_tasks[task_id]
            logger.info(f"[{self.agent_id}] Cancelled bid collection task for {task_id}.")

        if task_id in self.active_cfps:
            del self.active_cfps[task_id]
            logger.info(f"[{self.agent_id}] Removed CFP for task {task_id} from active_cfps.")

        task = self.tasks.get(task_id)
        if task:
            if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.status = TaskStatus.CANCELLED # Or BIDDING_FAILED if appropriate
                task.error_message = f"CFP process cancelled: {reason}"
                task.updated_at = datetime.utcnow()
                self.tasks[task_id] = task
                logger.info(f"[{self.agent_id}] Task {task_id} status updated to {task.status}.")
        else:
            logger.warning(f"[{self.agent_id}] Task {task_id} not found while cancelling CFP process.")

    async def _listen_for_task_results(self, task_id: str, result_submission_queue: str):
        logger.info(f"[{self.agent_id}] Listening for results for task {task_id} on queue {result_submission_queue}.")
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"[{self.agent_id}] Task {task_id} not found when starting to listen for results. Aborting listener.")
            if task_id in self.task_result_listeners:
                del self.task_result_listeners[task_id]
            return

        if not self.redis_pool:
            logger.error(f"[{self.agent_id}] Redis pool not available for listening to results of task {task_id}.")
            task.status = TaskStatus.FAILED
            task.error_message = "Result listening failed: Redis unavailable."
            task.failed_at = datetime.utcnow()
            self.tasks[task_id] = task
            if task_id in self.task_result_listeners:
                del self.task_result_listeners[task_id]
            return

        listen_timeout_seconds = 60  # Timeout for each BLPOP call
        max_listen_duration_seconds = task.deadline_seconds or self.default_task_deadline_seconds
        start_listen_time = datetime.utcnow()

        try:
            while True:
                current_duration = (datetime.utcnow() - start_listen_time).total_seconds()
                if current_duration >= max_listen_duration_seconds:
                    logger.warning(f"[{self.agent_id}] Task {task_id} exceeded max listen duration of {max_listen_duration_seconds}s. Marking as failed.")
                    task.status = TaskStatus.FAILED
                    task.error_message = "Task timed out waiting for result."
                    task.failed_at = datetime.utcnow()
                    self.tasks[task_id] = task
                    break
                
                remaining_time = max(0, max_listen_duration_seconds - current_duration)
                current_blpop_timeout = min(listen_timeout_seconds, int(remaining_time) + 1 if remaining_time > 0 else 0)

                if current_blpop_timeout <= 0:
                     logger.warning(f"[{self.agent_id}] Task {task_id} remaining time is zero or negative before BLPOP. Marking as failed.")
                     task.status = TaskStatus.FAILED
                     task.error_message = "Task timed out waiting for result (remaining time zero)."
                     task.failed_at = datetime.utcnow()
                     self.tasks[task_id] = task
                     break

                logger.debug(f"[{self.agent_id}] BLPOP on {result_submission_queue} for task {task_id} with timeout {current_blpop_timeout}s.")
                result_tuple = await self.redis_pool.blpop([result_submission_queue], timeout=current_blpop_timeout)

                if result_tuple:
                    _queue_name, result_json_str = result_tuple
                    logger.info(f"[{self.agent_id}] Received result for task {task_id} from {result_submission_queue}.")
                    
                    try:
                        result_data = json.loads(result_json_str)
                        if result_data.get("task_id") != task_id:
                            logger.warning(f"[{self.agent_id}] Received result for task {task_id} with mismatched task_id: {result_data.get('task_id')}. Continuing to listen.")
                            continue 
                        
                        result_message = TaskResultMessage(**result_data)
                        
                        task = self.tasks.get(task_id) 
                        if not task: 
                            logger.error(f"[{self.agent_id}] Task {task_id} disappeared during result processing! Cannot update status or record reputation.")
                            break

                        if task.status not in [TaskStatus.AWARDED, TaskStatus.IN_PROGRESS]:
                            logger.warning(f"[{self.agent_id}] Received result for task {task_id} but task status is {task.status}. Ignoring result.")
                            break

                        final_score = 0.0
                        final_comment = ""

                        if result_message.success:
                            task.status = TaskStatus.COMPLETED
                            task.result_data = result_message.result_data
                            task.completed_at = datetime.utcnow()
                            task.error_message = None 
                            logger.info(f"[{self.agent_id}] Task {task_id} completed successfully.")
                            final_score = 1.0
                            if task.assigned_to:
                                final_comment = f"Task {task_id} completed successfully by worker {task.assigned_to}."
                            else:
                                final_comment = f"Task {task_id} completed successfully (worker not specified in task.assigned_to)."
                        else:
                            task.status = TaskStatus.FAILED
                            task.error_message = result_message.error_message or "Task failed by worker without specific error."
                            task.result_data = result_message.result_data
                            task.failed_at = datetime.utcnow()
                            logger.warning(f"[{self.agent_id}] Task {task_id} failed. Reason: {task.error_message}")
                            final_score = 0.2
                            if task.assigned_to:
                                final_comment = f"Task {task_id} failed by worker {task.assigned_to}. Reason: {task.error_message}"
                            else:
                                final_comment = f"Task {task_id} failed (worker not specified in task.assigned_to). Reason: {task.error_message}"
                        
                        task.updated_at = datetime.utcnow()
                        self.tasks[task_id] = task

                        if self.registry_manager and task.assigned_to:
                            try:
                                rating = ReputationRating(
                                    rater_agent_id=self.agent_id,
                                    rated_agent_id=task.assigned_to,
                                    task_id=task_id,
                                    score=final_score,
                                    comment=final_comment
                                )
                                await self.registry_manager.record_rating(rating)
                                logger.info(f"[{self.agent_id}] Recorded rating for agent {task.assigned_to} for task {task_id}: score {final_score}")
                            except Exception as e_rep:
                                logger.error(f"[{self.agent_id}] Failed to record reputation for task {task_id}, agent {task.assigned_to}: {e_rep}", exc_info=True)
                        elif self.registry_manager and not task.assigned_to:
                            logger.warning(f"[{self.agent_id}] Cannot record rating for task {task_id} as it has no assigned worker. Skipping reputation update.")
                        
                        break # Exit while loop after processing a valid result

                    except json.JSONDecodeError as e_json:
                        logger.error(f"[{self.agent_id}] Error decoding result JSON for task {task_id}: {result_json_str}. Error: {e_json}. Continuing to listen.")
                    except ValidationError as e_val:
                        logger.error(f"[{self.agent_id}] Error validating TaskResultMessage for task {task_id}: {result_json_str}. Error: {e_val}. Continuing to listen.")
                    except Exception as e_proc:
                        logger.error(f"[{self.agent_id}] Unexpected error processing result for task {task_id}: {e_proc}", exc_info=True)
                        task = self.tasks.get(task_id)
                        if task and task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                            task.status = TaskStatus.FAILED
                            task.error_message = f"Internal error processing task result: {e_proc}"
                            task.failed_at = datetime.utcnow()
                            self.tasks[task_id] = task
                        break # Exit while loop on unexpected processing error
                else:
                    logger.debug(f"[{self.agent_id}] No result received for task {task_id} within timeout {current_blpop_timeout}s. Will retry.")
        
        except asyncio.CancelledError:
            logger.info(f"[{self.agent_id}] Result listener for task {task_id} was cancelled.")
            task = self.tasks.get(task_id)
            if task and task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                logger.warning(f"[{self.agent_id}] Task {task_id} listener cancelled. Current status: {task.status}. Marking as FAILED.")
                task.status = TaskStatus.FAILED 
                task.error_message = "Result listening cancelled before result received."
                task.failed_at = datetime.utcnow()
                task.updated_at = datetime.utcnow()
                self.tasks[task_id] = task
        except Exception as e_outer:
            logger.error(f"[{self.agent_id}] Unhandled error in result listener for task {task_id}: {e_outer}", exc_info=True)
            task = self.tasks.get(task_id)
            if task and task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.status = TaskStatus.FAILED 
                task.error_message = f"Result listening encountered an unhandled error: {e_outer}"
                task.failed_at = datetime.utcnow()
                task.updated_at = datetime.utcnow()
                self.tasks[task_id] = task
        finally:
            logger.info(f"[{self.agent_id}] Result listener for task {task_id} stopping.")
            if task_id in self.task_result_listeners:
                del self.task_result_listeners[task_id]

    async def stop(self):
        """Gracefully stop the agent, cancelling ongoing processes."""
        logger.info(f"[{self.agent_id}] TaskOrchestrationAgent stopping...")
        self.is_running = False # Signal loops to stop

        # Cancel all active CFP bid collection tasks
        for task_id, collection_task in list(self.cfp_bid_collection_tasks.items()): # list() for safe iteration while modifying
            logger.info(f"[{self.agent_id}] Cancelling bid collection for task {task_id} due to agent shutdown.")
            collection_task.cancel()
            try:
                await collection_task # Allow cancellation to propagate
            except asyncio.CancelledError:
                logger.debug(f"[{self.agent_id}] Bid collection task {task_id} confirmed cancelled.")
            except Exception as e:
                logger.error(f"[{self.agent_id}] Error during cancellation of bid collection task {task_id}: {e}", exc_info=True)
            if task_id in self.cfp_bid_collection_tasks: # Check if not already deleted by itself
                del self.cfp_bid_collection_tasks[task_id]
        self.active_cfps.clear()

        # Cancel all active task result listeners
        for task_id, listener_task in list(self.task_result_listeners.items()): # list() for safe iteration
            logger.info(f"[{self.agent_id}] Cancelling result listener for task {task_id} due to agent shutdown.")
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                logger.debug(f"[{self.agent_id}] Result listener task {task_id} confirmed cancelled.")
            except Exception as e:
                logger.error(f"[{self.agent_id}] Error during cancellation of result listener task {task_id}: {e}", exc_info=True)
            if task_id in self.task_result_listeners:
                del self.task_result_listeners[task_id]

        # BaseAgent's shutdown handles self.initialized and calls _shutdown.
        # _shutdown in TaskOrchestrationAgent should handle Redis closing.
        logger.info(f"[{self.agent_id}] Calling super().shutdown().")
        await super().shutdown() 

        logger.info(f"[{self.agent_id}] TaskOrchestrationAgent stopped successfully.")

    async def _shutdown(self) -> None:
        """Agent-specific shutdown logic, called by BaseAgent's shutdown."""
        logger.info(f"[{self.agent_id}] Executing _shutdown for TaskOrchestrationAgent...")
        if self.redis_pool:
            logger.info(f"[{self.agent_id}] Closing Redis connection pool in _shutdown.")
            try:
                await self.redis_pool.close()
                self.redis_pool = None
                logger.info(f"[{self.agent_id}] Redis connection pool closed in _shutdown.")
            except Exception as e:
                logger.error(f"[{self.agent_id}] Error closing Redis connection in _shutdown: {e}", exc_info=True)
        # Other TaskOrchestrationAgent-specific synchronous cleanup can go here.
        # self.initialized will be set to False by BaseAgent.shutdown() after this method completes.
        logger.info(f"[{self.agent_id}] _shutdown for TaskOrchestrationAgent completed.")
