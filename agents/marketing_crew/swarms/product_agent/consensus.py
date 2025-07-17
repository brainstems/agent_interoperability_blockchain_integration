from swarms.common.base import QueueWorker
from swarms.common.common import (
    logging,
    json,
    datetime,
    push_to_queue,
    handle_worker_error
)
import time

class ConsensusWorker(QueueWorker):
    """Consensus Worker implementation"""
    
    def __init__(self, input_queue, output_queue, worker_names, swarm_name, callback=None):
        # Initialize base class with required arguments
        super().__init__(
            name=f"{swarm_name}_consensus",
            input_queue=input_queue,
            output_queue=output_queue,
            callback=callback
        )
        self.expected_workers = {f'worker-{name}' for name in worker_names}
        self.worker_results = {}
        self.swarm_name = swarm_name
        logging.info(f"{swarm_name} consensus worker initialized with expected workers: {self.expected_workers}")
        
    def do_work(self, results):
        """Combine worker results into a single product strategy consensus"""
        # Extract worker results into a cleaner format
        consensus_data = {
            "timestamp": datetime.now().isoformat(),
            "worker_results": results,
            "combined_status": "completed",
            "worker_count": len(results),
            "summary": {
                "product_worker": next(
                    (result for result in results.values() 
                    if result.get('worker_name') == 'product_worker'),
                    {}
                ),
                "marketing_worker": next(
                    (result for result in results.values() 
                    if result.get('worker_name') == 'marketing_worker'),
                    {}
                )
            }
        }
        
        return {
            "consensus_result": consensus_data
        }
        
    async def process_message(self, data):
        if 'worker' in data and data['worker'] in self.expected_workers:
            worker_name = data['worker']
            if worker_name not in self.worker_results:
                logging.info(f"Received result from {worker_name}")
                self.worker_results[worker_name] = data
                
                if len(self.worker_results) == len(self.expected_workers):
                    logging.info("Generating consensus from worker results")
                    consensus = self.do_work(self.worker_results)
                    consensus['swarm_name'] = self.swarm_name
                    await self.send_output(consensus)
                    push_to_queue('consensus-output', consensus)
                    logging.info("Consensus generated and published")
                    self.worker_results = {}
                        
