from swarms.common.base import QueueWorker
from swarms.common.common import (
    logging,
    push_to_queue,
    handle_worker_error
)


class Leader(QueueWorker):
    """Leader implementation for product strategy swarm"""
    
    def __init__(self, input_queue, output_queue, callback=None):
        super().__init__("Product Strategy Leader", input_queue, output_queue, callback)
        
    def do_work(self, data):
        """Process and forward the message"""
        return data  # Leader just forwards the message
        
    async def process_message(self, data):
        logging.info("Leader: Forwarding message to product translation queue")
        result = self.do_work(data)
        if isinstance(result, dict):
            result['swarm_name'] = self.name
        await self.send_output(result)
        logging.info("Leader: Message forwarded successfully")
