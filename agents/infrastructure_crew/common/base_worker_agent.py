import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, Coroutine, Any, Dict, Union

from redis.asyncio import Redis as AsyncRedis
from pydantic import ValidationError

from .base_agent import BaseAgent, AgentConfig
from ..infrastructure_crew.schemas.task_schemas import TaskDefinition, TaskStatus, TaskUpdateRequest
# We need a way to access TaskOrchestrationAgent. This might be passed in or discovered.
# For now, let's assume it's passed in during initialization.
from ..infrastructure_crew.agents.task_orchestration_agent import TaskOrchestrationAgent

logger = logging.getLogger(__name__)

class BaseWorkerAgentConfig(AgentConfig):
    available_tasks_channel: str = "tasks:available"
    worker_capabilities: list[str] = [] # e.g., ["data_analysis", "report_generation"]
    
    class Config:
        extra = "allow"  # Allow extra fields for worker-specific configs

class BaseWorkerAgent(BaseAgent, ABC):
    def __init__(self, 
                 agent_id: str, 
                 redis_pool: AsyncRedis,
                 task_orchestrator: TaskOrchestrationAgent,
                 config: Optional[Union[Dict[str, Any], BaseWorkerAgentConfig]] = None):
        # Initialize with the agent_id and config
        super().__init__(agent_id, config or BaseWorkerAgentConfig(agent_id=agent_id))
        self.redis_pool = redis_pool
        self.task_orchestrator = task_orchestrator
        # Ensure config is of type BaseWorkerAgentConfig
        if not isinstance(self.config, BaseWorkerAgentConfig):
            self.config = BaseWorkerAgentConfig(agent_id=agent_id, **self.config.dict())
        self._subscriber_task: Optional[asyncio.Task] = None
        self.initialized = False

    async def initialize(self) -> bool:
        if not self.redis_pool:
            logger.error(f"[{self.agent_id}] Redis pool not provided. Cannot initialize.")
            return False
        if not self.task_orchestrator:
            logger.error(f"[{self.agent_id}] TaskOrchestrationAgent not provided. Cannot initialize.")
            return False
        logger.info(f"[{self.agent_id}] BaseWorkerAgent initializing with config: {self.config.dict()}")
        self.initialized = True
        logger.info(f"[{self.agent_id}] BaseWorkerAgent initialized.")
        return True

    async def start(self):
        if not self.initialized:
            logger.warning(f"[{self.agent_id}] Agent not initialized. Call initialize() first.")
            await self.initialize()
            if not self.initialized:
                 logger.error(f"[{self.agent_id}] Initialization failed. Cannot start subscriber task.")
                 return

        if self._subscriber_task is None or self._subscriber_task.done():
            self._subscriber_task = asyncio.create_task(self._redis_subscriber_loop())
            logger.info(f"[{self.agent_id}] Redis subscriber task started for available tasks.")
        else:
            logger.info(f"[{self.agent_id}] Redis subscriber task already running.")

    async def _redis_subscriber_loop(self):
        pubsub = self.redis_pool.pubsub()
        await pubsub.subscribe(self.config.available_tasks_channel)
        logger.info(f"[{self.agent_id}] Subscribed to Redis channel: {self.config.available_tasks_channel}")

        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    channel = message['channel'].decode('utf-8')
                    data_str = message['data'].decode('utf-8')
                    logger.debug(f"[{self.agent_id}] Received message on {channel}")
                    await self._handle_available_task(data_str)
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            logger.info(f"[{self.agent_id}] Redis subscriber loop cancelled.")
        except aioredis.RedisError as e:
            logger.error(f"[{self.agent_id}] Redis error in subscriber loop: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"[{self.agent_id}] Unexpected error in subscriber loop: {e}", exc_info=True)
        finally:
            logger.info(f"[{self.agent_id}] Unsubscribing from {self.config.available_tasks_channel}.")
            await pubsub.unsubscribe(self.config.available_tasks_channel)
            await pubsub.close()
    
    async def _handle_available_task(self, task_data_str: str):
        try:
            task = TaskDefinition.parse_raw(task_data_str)
        except (ValidationError, json.JSONDecodeError) as e:
            logger.error(f"[{self.agent_id}] Error parsing TaskDefinition from Redis: {e} - Data: {task_data_str[:200]}")
            return

        if task.status == TaskStatus.READY and await self.can_execute_task(task):
            logger.info(f"[{self.agent_id}] Matched for task {task.task_id} ({task.name}). Attempting to claim.")
            
            claim_update = TaskUpdateRequest(status=TaskStatus.IN_PROGRESS, assigned_to=self.agent_id)
            updated_task = await self.task_orchestrator.update_task(task.task_id, claim_update)

            if updated_task and updated_task.status == TaskStatus.IN_PROGRESS and updated_task.assigned_to == self.agent_id:
                logger.info(f"[{self.agent_id}] Successfully claimed task {task.task_id}.")
                try:
                    result = await self.execute_task(updated_task)
                    final_status_update = TaskUpdateRequest(status=TaskStatus.COMPLETED, result=result)
                    logger.info(f"[{self.agent_id}] Task {task.task_id} completed successfully.")
                except Exception as e:
                    logger.error(f"[{self.agent_id}] Error executing task {task.task_id}: {e}", exc_info=True)
                    final_status_update = TaskUpdateRequest(status=TaskStatus.FAILED, error_message=str(e))
                
                await self.task_orchestrator.update_task(task.task_id, final_status_update)
            elif updated_task:
                logger.info(f"[{self.agent_id}] Failed to claim task {task.task_id}. Current status: {updated_task.status}, Assigned: {updated_task.assigned_to}")
            else:
                logger.warning(f"[{self.agent_id}] Task {task.task_id} could not be found or updated during claim attempt.")
        else:
            logger.debug(f"[{self.agent_id}] Not matched or task {task.task_id} not READY (status: {task.status}). Skipping.")

    @abstractmethod
    async def can_execute_task(self, task: TaskDefinition) -> bool:
        """Subclasses must implement this to decide if they can handle the task."""
        pass

    @abstractmethod
    async def execute_task(self, task: TaskDefinition) -> Any:
        """Subclasses must implement this to perform the actual task work."""
        pass

    async def stop(self):
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                logger.info(f"[{self.agent_id}] Subscriber task cancelled.")
            self._subscriber_task = None
        self.initialized = False
        logger.info(f"[{self.agent_id}] BaseWorkerAgent stopped.")
