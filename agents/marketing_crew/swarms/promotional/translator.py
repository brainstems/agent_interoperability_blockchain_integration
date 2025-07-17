from swarms.common.base import QueueWorker
from swarms.common.common import (
    logging,
    datetime,
    push_to_queue,
    handle_worker_error
)
from swarms.promotional.agent.translator import TranslatorCrew


class TranslationAgent(QueueWorker):
    """Translation Agent implementation"""
    
    def __init__(self, input_queue, output_queue, worker_names, callback=None):
        super().__init__("Translation Agent", input_queue, output_queue, callback)
        self.worker_names = worker_names
        logging.info(f"Translation agent initialized with workers: {self.worker_names}")
        
    def do_work(self, data):
        """Process work using TranslatorCrew"""
        translator = TranslatorCrew()
        worker_messages = translator.process({
            "worker_names": self.worker_names,
            "input_data": data
        })  
        
        return worker_messages
        
    async def process_message(self, data):
        logging.info("Processing translation request")
        
        worker_messages = self.do_work(data)
        swarm_name = data.get('swarm_name', 'promotional')
        
        for msg in worker_messages:
            msg['swarm_name'] = swarm_name
            await self.send_output(msg)
            logging.info(f"Generated worker message: {msg['type']}")
        
        await self.send_output({
            "status": "completed",
            "message": "Generated worker tasks",
            "swarm_name": swarm_name,
            "timestamp": datetime.now().isoformat()
        })
            
