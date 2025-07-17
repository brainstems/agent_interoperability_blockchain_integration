import asyncio
import logging
from typing import Optional, Any

from redis.asyncio import Redis as AsyncRedis

from agents.infrastructure_crew.common.base_worker_agent import BaseWorkerAgent, BaseWorkerAgentConfig
from agents.infrastructure_crew.schemas.task_schemas import TaskDefinition
from agents.infrastructure_crew.infrastructure_agents.task_orchestration_agent import TaskOrchestrationAgent

logger = logging.getLogger(__name__)

class ExampleWorkerAgentConfig(BaseWorkerAgentConfig):
    worker_name: str = "ExampleWorker"
    handled_task_name: str = "example_task"

class ExampleWorkerAgent(BaseWorkerAgent):
    def __init__(self,
                 agent_id: str,
                 redis_pool: AsyncRedis,
                 task_orchestrator: TaskOrchestrationAgent,
                 config: Optional[ExampleWorkerAgentConfig] = None):
        super().__init__(agent_id, redis_pool, task_orchestrator, config or ExampleWorkerAgentConfig())
        self.config: ExampleWorkerAgentConfig = self.config # For type hinting

    async def can_execute_task(self, task: TaskDefinition) -> bool:
        """Can execute if the task name matches the configured handled_task_name."""
        can_handle = task.name == self.config.handled_task_name
        if can_handle:
            logger.info(f"[{self.agent_id}] Can execute task {task.task_id} (name: {task.name})")
        else:
            logger.debug(f"[{self.agent_id}] Cannot execute task {task.task_id} (name: {task.name}), looking for '{self.config.handled_task_name}'.")
        return can_handle

    async def execute_task(self, task: TaskDefinition) -> Any:
        """Simulates executing a task."""
        logger.info(f"[{self.agent_id}] Executing task {task.task_id} (name: {task.name}). Data: {task.data}")
        
        # Simulate work
        await asyncio.sleep(5) 
        
        result_message = f"Task {task.name} processed successfully by {self.agent_id}."
        logger.info(f"[{self.agent_id}] Finished executing task {task.task_id}. Result: {result_message}")
        return {"message": result_message, "details": "Simulation complete"}

    async def get_agent_details(self) -> dict:
        base_details = await super().get_agent_details()
        base_details.update({
            "worker_name": self.config.worker_name,
            "handled_task_name": self.config.handled_task_name,
            "type": "ExampleWorkerAgent"
        })
        return base_details
