from abc import ABC, abstractmethod
from swarms.common.common import (
    logging,
    json,
    datetime,
    get_redis_client,
    push_to_queue,
    get_from_queue,
    handle_worker_error
)


class BaseWorker(ABC):
    """Base class for all workers in swarm systems"""
    
    def __init__(self, name, input_queue, output_queue, callback=None):
        self.name = name
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.redis_client = None
        self.callback = callback or (lambda x: x)  # Default to identity function
        
    def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = get_redis_client()
            logging.info(f"{self.name} starting... [in: {self.input_queue}, out: {self.output_queue}]")
        except Exception as e:
            logging.error(f"Failed to initialize Redis: {str(e)}")
            raise
            
    def shutdown(self):
        """Cleanup resources"""
        if self.redis_client:
            self.redis_client.close()
            logging.info(f"Shutting down {self.name}...")
            
    @abstractmethod
    async def process_message(self, data):
        """Process incoming message"""
        pass
        
    async def run(self):
        """Main worker loop"""
        try:
            self.initialize()
            
            while True:
                try:
                    message = get_from_queue(self.redis_client, self.input_queue)
                    if message:
                        logging.info(f"{self.name}: Received raw message: {message}")
                        logging.info(f"{self.name}: Message type: {type(message)}")
                        
                        try:
                            # Handle different message formats
                            if isinstance(message, (list, tuple)):
                                logging.info(f"{self.name}: Processing tuple/list message: {message}")
                                # Extract the actual message content from the tuple (queue_name, message)
                                message_data = message[1]
                            else:
                                logging.info(f"{self.name}: Processing direct message: {message}")
                                message_data = message

                            # Handle bytes or string
                            if isinstance(message_data, bytes):
                                message_data = message_data.decode('utf-8')
                                logging.info(f"{self.name}: Decoded bytes to string: {message_data}")

                            # Parse JSON
                            logging.info(f"{self.name}: Attempting to parse JSON: {message_data}")
                            if isinstance(message_data, str):
                                data = json.loads(message_data)
                            else:
                                data = message_data
                            
                            logging.info(f"{self.name}: Successfully parsed message data: {data}")
                            await self.process_message(data)
                            
                        except (IndexError, TypeError) as e:
                            logging.error(f"{self.name}: Invalid message format: {str(e)}")
                            logging.error(f"{self.name}: Message details - Type: {type(message)}, Content: {message}")
                            continue
                        except json.JSONDecodeError as e:
                            logging.error(f"{self.name}: JSON decode error: {str(e)}")
                            logging.error(f"{self.name}: Failed to parse message: {message_data}")
                            continue
                        except Exception as e:
                            logging.error(f"{self.name}: Unexpected error processing message: {str(e)}")
                            logging.error(f"{self.name}: Full error details:", exc_info=True)
                            continue
                            
                except KeyboardInterrupt:
                    logging.info(f"{self.name}: Received keyboard interrupt, shutting down...")
                    break
                except Exception as e:
                    logging.error(f"{self.name}: Error in main loop: {str(e)}")
                    logging.error(f"{self.name}: Full error details:", exc_info=True)
                    continue
                
        finally:
            self.shutdown()

    async def publish_event(self, event_type, data):
        """Base work method with event publishing"""
        return data
        pass

    async def send_output(self, data):
        """Send output data through callback and to queue"""
        logging.info(f"{self.name}: Processing output data through callback")
        processed_data = self.callback(data)
        # Handle if callback returns a coroutine
        if hasattr(processed_data, '__await__'):
            processed_data = await processed_data
            logging.info(f"{self.name}: Awaited coroutine result")
        
        logging.info(f"{self.name}: Pushing data to output queue: {self.output_queue}")
        push_to_queue(self.redis_client, self.output_queue, processed_data)
        logging.info(f"{self.name}: Successfully pushed data to output queue")


class TaskWorker(BaseWorker):
    """Base class for workers that process specific tasks"""
    
    def __init__(self, name, worker_type, input_queue, output_queue, callback=None):
        super().__init__(name, input_queue, output_queue, callback)
        self.worker_type = worker_type
        
    async def process_message(self, data):
        """Process only messages of matching type"""
        if data.get('type') == self.worker_type:
            logging.info(f"Received {self.worker_type} message")
            await self.process_task(data)
            
    @abstractmethod
    async def process_task(self, data):
        """Process specific worker task"""
        pass

    pass 


class QueueWorker(BaseWorker):
    """Base class for workers that process queue messages"""
    pass
