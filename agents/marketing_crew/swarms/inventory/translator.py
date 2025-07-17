import time
from swarms.common.base import QueueWorker
from swarms.common.common import (
    logging,
    json,
    datetime,
    push_to_queue,
    handle_worker_error
)
from swarms.inventory.agent.translator import InventoryTranslationAgent
from swarms.memory.agent import Agent, EntityState, Memory
from typing import List, Optional


class TranslationWorker(QueueWorker):
    """Translation worker for inventory management"""
    
    def __init__(self, input_queue, output_queue, worker_names, callback=None):
        super().__init__("Inventory Translation Worker", input_queue, output_queue, callback)
        self.worker_names = worker_names
        self.translation_agent = InventoryTranslationAgent()
        self.agent_memory = Agent(
            agent_id="translation_worker",
            swarm_id="inventory_management",
            storage_dir="memories/translation"
        )
        logging.info(f"Inventory translation worker initialized for workers: {worker_names}")
        
    def do_work(self, data):
        """Process inventory message through translation agent"""
        try:
            original_message = data.get('message', '')
            task_id = data.get('task_id', 'unknown')
            swarm_name = data.get('swarm_name', 'inventory')  # Preserve swarm name
            
            # Process through CrewAI agent
            result = self.translation_agent.process(original_message)
            
            # Create tasks for each worker
            tasks = []
            for worker_name in self.worker_names:
                task = {
                    'worker': f'worker-{worker_name}',
                    'task_id': f"{task_id}-{worker_name}",
                    'type': worker_name.split('_')[0],
                    'data': result,
                    'original_message': original_message,
                    'swarm_name': swarm_name,  # Add swarm name
                    'timestamp': datetime.now().isoformat()
                }
                tasks.append(task)
            
            # Store memory of this translation
            memory_id = f"translation_{task_id}_{int(time.time())}"
            
            # Create entity states for the tasks
            entities = [
                EntityState(
                    entity_id=task['task_id'],
                    entity_type="translation_task",
                    attributes={
                        "worker": task['worker'],
                        "type": task['type'],
                        "timestamp": task['timestamp']
                    }
                )
                for task in tasks
            ]
            
            # Store the translation interaction in memory
            self.agent_memory.create_memory(
                memory_id=memory_id,
                context={
                    "task_id": task_id,
                    "worker_names": self.worker_names
                },
                prompt=original_message,
                output={
                    "translated_result": result,
                    "generated_tasks": tasks
                },
                agent_state={
                    "completed_actions": [{
                        "type": "translation",
                        "timestamp": datetime.now().isoformat()
                    }],
                    "solution_state": {
                        "task_completed": True,
                        "num_tasks_generated": len(tasks)
                    }
                },
                entities=entities,
                memory_level="personal"
            )
            
            return tasks
            
        except Exception as e:
            handle_worker_error(self.redis_client, e, "inventory_translation")
            return []
        
    async def process_message(self, data):
        logging.info(f"Translating inventory message: {data.get('task_id')}")
        tasks = self.do_work(data)
        
        # Send each task to the worker queue
        for task in tasks:
            await self.send_output(task)
            logging.info(f"Task created for {task['worker']} marketing agent")
    
    def get_translation_history(
        self,
        start_time: Optional[datetime]=None,
        end_time: Optional[datetime]=None
    ) -> List[Memory]:
        """Retrieve history of translations"""
        if start_time and end_time:
            return self.agent_memory.get_memories_by_timerange(start_time, end_time)
        return self.agent_memory.get_all_memories()
              
