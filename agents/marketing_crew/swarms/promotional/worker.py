from swarms.common.base import TaskWorker
from swarms.common.common import (
    logging,
    datetime,
    handle_worker_error
)
from swarms.promotional.agent.worker_crew import WorkerCrew
import time


class SimpleWorker(TaskWorker):
    """Simple worker implementation with sleep"""
    
    def __init__(self, worker_name, input_queue, output_queue, callback=None):
        super().__init__(
            name=f"Worker {worker_name}",
            worker_type=f"worker-{worker_name.lower()}",
            input_queue=input_queue,
            output_queue=output_queue,
            callback=callback
        )
        self.worker_name = worker_name
        
    def do_work(self, data):
        """Simple processing with sleep"""
        time.sleep(2)
        return {
            "task_id": data["task_id"],
            "worker_name": self.worker_name,
            "status": "completed",
            "message": "Task processed successfully",
            "swarm_name": data.get('swarm_name', 'promotional'),
            "timestamp": datetime.now().isoformat()
        }
        
    async def process_task(self, data):
        logging.info(f"Worker {self.worker_name} processing task: {data['task_id']}")
            
        response = self.do_work(data)
        await self.send_output(response)
        logging.info(f"Worker {self.worker_name} completed task: {data['task_id']}")
            

class CrewWorker(TaskWorker):
    """Worker implementation using CrewAI"""
    
    def __init__(self, worker_name, input_queue, output_queue, callback=None):
        super().__init__(
            name=f"Worker {worker_name}",
            worker_type=f"worker-{worker_name.lower()}",
            input_queue=input_queue,
            output_queue=output_queue,
            callback=callback
        )
        self.worker_name = worker_name
        
    def do_work(self, data):
        """Process work using WorkerCrew"""
        worker = WorkerCrew(self.worker_name)
        result = worker.process(data)
        result['swarm_name'] = data.get('swarm_name', 'promotional')
        return result
        
    async def process_task(self, data):
            
        await self.publish_event('task_started', data)
        response = self.do_work(data)
        await self.publish_event('task_completed', response)
        logging.info(f"Worker {self.worker_name} completed task: {data['task_id']}")
      
