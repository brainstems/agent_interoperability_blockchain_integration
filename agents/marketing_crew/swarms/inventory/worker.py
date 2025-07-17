from swarms.common.base import TaskWorker
from swarms.common.common import (
    logging,
    handle_worker_error
)
from swarms.inventory.agent.worker_crew import InventoryWorkerCrew
from datetime import datetime


class InventoryWorker(TaskWorker):
    """Worker implementation for inventory management"""
    
    def __init__(self, worker_name, input_queue, output_queue, callback=None):
        super().__init__(
            name=f"Worker {worker_name}",
            worker_type=f"worker-{worker_name.lower()}",
            input_queue=input_queue,
            output_queue=output_queue,
            callback=callback
        )
        self.worker_name = worker_name
        self.worker_crew = InventoryWorkerCrew()
        
    def do_work(self, data):
        """Process work using InventoryWorkerCrew"""
        result = self.worker_crew.process(data)
        return {
            'worker': f'worker-{self.worker_name}',
            'worker_name': self.worker_name,
            'task_id': data.get('task_id'),
            'type': 'inventory',
            'result': result,
            'swarm_name': data.get('swarm_name', 'inventory'),
            'timestamp': datetime.now().isoformat()
        }
        
    async def process_task(self, data):
        logging.info(f"Worker {self.worker_name} processing task: {data.get('task_id')}")
        response = self.do_work(data)
        await self.send_output(response)
        logging.info(f"Worker {self.worker_name} completed task: {data.get('task_id')}")


class OptimizationWorker(TaskWorker):
    """Worker implementation for inventory optimization"""
    
    def __init__(self, worker_name, input_queue, output_queue, callback=None):
        super().__init__(
            name=f"Worker {worker_name}",
            worker_type=f"worker-{worker_name.lower()}",
            input_queue=input_queue,
            output_queue=output_queue,
            callback=callback
        )
        self.worker_name = worker_name
        self.worker_crew = InventoryWorkerCrew()  # Using same crew but with different focus
        
    def do_work(self, data):
        """Process work using InventoryWorkerCrew with optimization focus"""
        # Add optimization specific context
        data['optimization_context'] = {
            'focus': 'stock_optimization',
            'metrics': ['reorder_points', 'safety_stock', 'lead_time']
        }
        
        result = self.worker_crew.process(data)
        return {
            'worker': f'worker-{self.worker_name}',
            'worker_name': self.worker_name,
            'task_id': data.get('task_id'),
            'type': 'optimization',
            'result': result,
            'swarm_name': data.get('swarm_name', 'inventory'),
            'timestamp': datetime.now().isoformat()
        }
        
    async def process_task(self, data):
        logging.info(f"Worker {self.worker_name} processing task: {data.get('task_id')}")
        response = self.do_work(data)
        await self.send_output(response)
        logging.info(f"Worker {self.worker_name} completed task: {data.get('task_id')}")  
