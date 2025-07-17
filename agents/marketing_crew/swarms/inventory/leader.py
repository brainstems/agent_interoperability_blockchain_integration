from swarms.common.base import QueueWorker
from swarms.common.common import (
    logging,
    push_to_queue,
    handle_worker_error
)
import time


class Leader(QueueWorker):
    """Leader implementation for inventory swarm"""
    
    def __init__(self, input_queue, output_queue, callback=None):
        super().__init__("Inventory Leader", input_queue, output_queue, callback)
        
    def do_work(self, data):
        """Simulate work processing"""
        time.sleep(2)  # Simulate work
        return data  # Leader just forwards the message
        
    async def process_message(self, data):
        logging.info("Leader: Forwarding message to inventory translation queue")
        result = self.do_work(data)
        # Ensure swarm_name is preserved
        if isinstance(result, dict):
            result['swarm_name'] = self.name
        await self.send_output(result)
        logging.info("Leader: Message forwarded successfully")
