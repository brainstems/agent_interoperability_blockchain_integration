from swarms.common.base import TaskWorker
from swarms.common.common import (
    logging,
    handle_worker_error
)
from swarms.product_agent.agent.worker_crew import ProductWorkerCrew
from datetime import datetime


class ProductWorker(TaskWorker):
    """Worker implementation for product strategy"""
    
    def __init__(self, worker_name, input_queue, output_queue, callback=None):
        super().__init__(
            name=f"Worker {worker_name}",
            worker_type=f"worker-{worker_name.lower()}",
            input_queue=input_queue,
            output_queue=output_queue,
            callback=callback
        )
        self.worker_name = worker_name
        self.worker_crew = ProductWorkerCrew()
        
    def do_work(self, data):
        """Process work using ProductWorkerCrew"""
        result = self.worker_crew.process(data)
        return {
            'worker': f'worker-{self.worker_name}',
            'worker_name': self.worker_name,
            'task_id': data.get('task_id'),
            'type': 'product_strategy',
            'result': result,
            'swarm_name': data.get('swarm_name', 'product_agent'),
            'timestamp': datetime.now().isoformat()
        }
        
    async def process_task(self, data):
        logging.info(f"Worker {self.worker_name} processing task: {data.get('task_id')}")
        response = self.do_work(data)
        await self.send_output(response)
        logging.info(f"Worker {self.worker_name} completed task: {data.get('task_id')}")

            
class MarketingWorker(TaskWorker):
    """Worker implementation for marketing strategy"""
    
    def __init__(self, worker_name, input_queue, output_queue, callback=None):
        super().__init__(
            name=f"Worker {worker_name}",
            worker_type=f"worker-{worker_name.lower()}",
            input_queue=input_queue,
            output_queue=output_queue,
            callback=callback
        )
        self.worker_name = worker_name
        self.worker_crew = ProductWorkerCrew()  # Using same crew but with marketing focus
        
    def do_work(self, data):
        """Process work using ProductWorkerCrew with marketing focus"""
        # Add marketing specific context
        data['marketing_context'] = {
            'focus': 'channel_optimization',
            'metrics': ['customer_acquisition', 'channel_performance', 'advertising_roi']
        }
        
        result = self.worker_crew.process(data)
        return {
            'worker': f'worker-{self.worker_name}',
            'worker_name': self.worker_name,
            'task_id': data.get('task_id'),
            'type': 'marketing_strategy',
            'result': result,
            'swarm_name': data.get('swarm_name', 'product_agent'),
            'timestamp': datetime.now().isoformat()
        }
        
    async def process_task(self, data):
        logging.info(f"Worker {self.worker_name} processing task: {data.get('task_id')}")
        response = self.do_work(data)
        await self.send_output(response)
        logging.info(f"Worker {self.worker_name} completed task: {data.get('task_id')}")
