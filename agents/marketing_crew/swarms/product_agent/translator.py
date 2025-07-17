from swarms.common.base import QueueWorker
from swarms.common.common import (
    logging,
    json,
    datetime,
    push_to_queue,
    handle_worker_error
)
from swarms.product_agent.agent.worker_crew import ProductWorkerCrew


class TranslationWorker(QueueWorker):
    """Translation worker for product strategy"""
    
    def __init__(self, input_queue, output_queue, worker_names, callback=None):
        super().__init__("Product Translation Worker", input_queue, output_queue, callback)
        self.worker_names = worker_names
        self.translation_agent = ProductWorkerCrew()
        logging.info(f"Product translation worker initialized for workers: {worker_names}")
        
    def do_work(self, data):
        """Process product strategy message through translation agent"""
        try:
            # Process through CrewAI agent
            result = self.translation_agent.process({
                'message': data.get('message', ''),
                'metrics': data.get('metrics', {}),
                'redis_client': self.redis_client
            })
            
            # Create tasks for each worker
            tasks = []
            swarm_name = data.get('swarm_name', 'product_agent')
            for worker_name in self.worker_names:
                task = {
                    'worker': f'worker-{worker_name}',
                    'task_id': f"{data.get('task_id', 'unknown')}-{worker_name}",
                    'type': worker_name.split('_')[0],  # 'product' or 'marketing'
                    'data': result,
                    'original_message': data.get('message', ''),
                    'metrics': data.get('metrics', {}),
                    'swarm_name': swarm_name,
                    'timestamp': datetime.now().isoformat()
                }
                tasks.append(task)
            
            return tasks
            
        except Exception as e:
            handle_worker_error(self.redis_client, e, "product_translation")
            return []
        
    async def process_message(self, data):
        logging.info(f"Translating product strategy message: {data.get('task_id')}")
        tasks = self.do_work(data)
            
            # Send each task to the worker queue
        for task in tasks:
            await self.send_output(task)
            logging.info(f"Task created for {task['worker']} product agent")
  
