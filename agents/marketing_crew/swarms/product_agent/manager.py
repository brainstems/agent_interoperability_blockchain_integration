import threading
from concurrent.futures import ThreadPoolExecutor
from swarms.common.base import QueueWorker
from swarms.common.common import (
    logging,
    get_redis_client,
    handle_worker_error
)
from swarms.product_agent.worker import ProductWorker, MarketingWorker
from swarms.product_agent.leader import Leader
from swarms.product_agent.translator import TranslationWorker
from swarms.product_agent.consensus import ConsensusWorker
import json
import requests
from swarms.common.api import store_agent_state, store_agent_event
import time
import traceback
from datetime import datetime
import asyncio


class ProductSwarmManager:
    """Manager class to orchestrate all product swarm components"""
    
    # Queue configuration
    QUEUES = {
        'product_swarm': 'product-swarm',
        'shared_channel': 'state-swarm',  # Update shared pub/sub channel
        'translation': 'product-translator',
        'worker': 'product-worker-queue',
        'consensus': 'product-consensus',
        'error': 'error-queue',
        'api_query': 'api_queue'
    }
    
    def __init__(self, swarm_name):
        self.swarm_name = swarm_name
        self.workers = {}
        self.threads = {}
        self.running = False
        self.redis_client = None
        # Define worker names
        self.worker_names = ['product_worker', 'marketing_worker']
        # Add callback methods
        self.callbacks = {
            'leader': self.leader_callback,
            'translation': self.translation_callback,
            'consensus': self.consensus_callback,
            'worker': self.worker_callback
        }
        # Add API endpoint
        self.state_api_endpoint = "https://hash-storage-test.zeljko.dev/api/state/1"
        
    # Update callback methods
    async def leader_callback(self, data):
        logging.info(f"Leader output: {data}")
        
        # Push to API queue
        api_message = {
            "message": data,
            "type": f"{self.swarm_name}_leader"
        }
        self.redis_client.rpush(self.QUEUES['api_query'], json.dumps(api_message))

        # Store queue push event
        event_data = {
            "type": "queue_push",
            "queue": self.QUEUES['api_query'],
            "message_type": "leader_output",
            "timestamp": datetime.now().isoformat(),
            "data": api_message,
            "swarm_name": self.swarm_name
        }
        await store_agent_event(
            event_id=f"queue_push_{int(time.time())}",
            agent_id=f"{self.swarm_name}_leader",
            event_data=event_data
        )
        
        # Store leader output event
        event_data = {
            "type": "leader_output",
            "worker": self.swarm_name,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "swarm_name": self.swarm_name
        }
        await store_agent_event(
            event_id=f"leader_{int(time.time())}",
            agent_id=f"{self.swarm_name}_leader",
            event_data=event_data
        )
        
        state_data = {
            "agentId": f"{self.swarm_name}_leader",
            "memoryType": "product_swarm_leader_state",
            "attributes": data
        }
        try:
            result = await store_agent_state(f"{self.swarm_name}_leader", state_data)
            logging.info(f"Leader state stored successfully: {result}")
        except Exception as e:
            logging.error(f"Failed to store leader state: {str(e)}\nTraceback:\n{traceback.format_exc()}")
        
        return data

    async def translation_callback(self, data):
        logging.info(f"Translation output: {data}")
        self.redis_client.rpush(self.QUEUES['api_query'], json.dumps({
            "type": f"{self.swarm_name}_translation",
            "message": str(data),
            "swarm_name": self.swarm_name
        }))
        
        # Store event in external API
        try:
            event_data = {
                "type": "translation_output",
                "worker": self.swarm_name,
                "timestamp": datetime.now().isoformat(),
                "data": data,
                "swarm_name": self.swarm_name
            }
            await store_agent_event(
                event_id=f"translation_{int(time.time())}",
                agent_id=f"{self.swarm_name}_translator",
                event_data=event_data
            )
            logging.info("Translation event stored successfully")
        except Exception as e:
            logging.error(f"Failed to store translation event: {str(e)}\nTraceback:\n{traceback.format_exc()}")
            
        state_data = {
            "agentId": f"{self.swarm_name}_translator",
            "memoryType": "product_swarm_translation_state",
            "attributes": data
        }
        try:
            result = await store_agent_state(f"{self.swarm_name}_translator", state_data)
            logging.info(f"Translation state stored successfully: {result}")
        except Exception as e:
            logging.error(f"Failed to store translation state: {str(e)}\nTraceback:\n{traceback.format_exc()}")
            
        return data

    async def consensus_callback(self, data):
        logging.info(f"Consensus output: {data}")
        self.redis_client.rpush(self.QUEUES['api_query'], json.dumps({
            "type": f"{self.swarm_name}_consensus",
            "message": str(data),
            "swarm_name": self.swarm_name
        }))
        
        state_data = {
            "agentId": f"{self.swarm_name}_consensus",
            "memoryType": "product_swarm_consensus_state",
            "attributes": data
        }
        try:
            result = await store_agent_state(f"{self.swarm_name}_consensus", state_data)
            logging.info(f"Consensus state stored successfully: {result}")
        except Exception as e:
            logging.error(f"Failed to store consensus state: {str(e)}\nTraceback:\n{traceback.format_exc()}")
            
        return data

    async def worker_callback(self, data):
        logging.info(f"Worker output: {data}")
        self.redis_client.rpush(self.QUEUES['api_query'], json.dumps({
            "type": f"{self.swarm_name}_worker",
            "message": str(data),
            "swarm_name": self.swarm_name
        }))
        
        worker_id = data.get("worker_id", "worker")
        state_data = {
            "agentId": worker_id,
            "memoryType": "product_swarm_worker_state",
            "attributes": data
        }
        try:
            result = await store_agent_state(worker_id, state_data)
            logging.info(f"Worker state stored successfully: {result}")
        except Exception as e:
            logging.error(f"Failed to store worker state: {str(e)}\nTraceback:\n{traceback.format_exc()}")
            
        return data

    def initialize(self):
        """Initialize Redis connection and create worker instances"""
        try:
            self.redis_client = get_redis_client()
            
            # Subscribe to shared channel
            self.pubsub = self.redis_client.pubsub()
            logging.info(f"[{self.swarm_name}] Subscribing to shared channel: {self.QUEUES['shared_channel']}")
            self.pubsub.subscribe(self.QUEUES['shared_channel'])
            
            # Verify subscription
            for subscription in self.pubsub.channels.keys():
                logging.info(f"[{self.swarm_name}] Successfully subscribed to channel: {subscription}")
            
            # Start pubsub listener thread
            self.pubsub_thread = threading.Thread(
                target=lambda: asyncio.run(self.handle_pubsub_messages()),
                name=f"{self.swarm_name}_pubsub_listener",
                daemon=True
            )
            self.pubsub_thread.start()
            logging.info(f"[{self.swarm_name}] Started pubsub listener thread")
            
            logging.info(f"[{self.swarm_name}] Product Swarm Manager initializing...")
            
            # Initialize base components with callbacks
            self.workers = {
                'leader': Leader(
                    input_queue=self.QUEUES['product_swarm'],
                    output_queue=self.QUEUES['translation'],
                    callback=self.callbacks['leader']
                ),
                'translation': TranslationWorker(
                    input_queue=self.QUEUES['translation'],
                    output_queue=self.QUEUES['worker'],
                    callback=self.callbacks['translation'],
                    worker_names=self.worker_names
                ),
                'consensus': ConsensusWorker(
                    input_queue=self.QUEUES['consensus'],
                    output_queue=self.QUEUES['product_swarm'],
                    callback=self.callbacks['consensus'],
                    worker_names=self.worker_names,
                    swarm_name=self.swarm_name
                )
            }
            
            # Initialize workers
            self.workers['product_worker'] = ProductWorker(
                worker_name='product_worker',
                input_queue=self.QUEUES['worker'],
                output_queue=self.QUEUES['consensus'],
                callback=self.callbacks['worker']
            )
            
            self.workers['marketing_worker'] = MarketingWorker(
                worker_name='marketing_worker',
                input_queue=self.QUEUES['worker'],
                output_queue=self.QUEUES['consensus'],
                callback=self.callbacks['worker']
            )
            
            # Log queue configuration
            logging.info("Queue Configuration:")
            for worker_name, worker in self.workers.items():
                logging.info(f"{worker_name}: {worker.input_queue} -> {worker.output_queue}")
            
        except Exception as e:
            logging.error(f"Failed to initialize Product Strategy Swarm Manager: {str(e)}\nTraceback:\n{traceback.format_exc()}")
            raise
            
    def start_worker(self, name, worker):
        """Start a worker in a separate thread"""
        try:
            logging.info(f"Starting {name}...")
            # Create new event loop for the thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the worker's run coroutine in the event loop
            thread = threading.Thread(
                target=lambda: loop.run_until_complete(worker.run()),
                name=name,
                daemon=True
            )
            thread.start()
            self.threads[name] = thread
            logging.info(f"{name} started successfully")
        except Exception as e:
            handle_worker_error(self.redis_client, e, f"manager-{name}")
            
    def start(self):
        """Start all workers in separate threads"""
        try:
            self.initialize()
            self.running = True
            
            # Start workers in specific order
            startup_sequence = [
                'consensus',  # Start consensus first to handle results
                'product_worker', 'marketing_worker',  # Start all workers
                'translation',  # Start translation before leader
                'leader'  # Start leader last
            ]
            
            with ThreadPoolExecutor(max_workers=len(self.workers)) as executor:
                for worker_name in startup_sequence:
                    if worker_name in self.workers:
                        executor.submit(
                            self.start_worker,
                            worker_name,
                            self.workers[worker_name]
                        )
                        
            logging.info("All workers started successfully")
            
            # Wait for all threads
            while self.running:
                for name, thread in self.threads.items():
                    if not thread.is_alive():
                        logging.error(f"[{self.swarm_name}] {name} has stopped unexpectedly")
                        self.running = False
                        break
                    thread.join(timeout=1.0)
                    
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            logging.error(f"Error in manager: {str(e)}")
            self.stop()
            
    async def handle_pubsub_messages(self):
        """Handle messages from the shared pub/sub channel"""
        logging.info(f"[{self.swarm_name}] Starting pubsub message handler")
        logging.info(f"[{self.swarm_name}] Running status: {self.running}")
        
        while self.running:
            try:
                message = self.pubsub.get_message(timeout=1.0)
                
                if message:
                    logging.info(f"[{self.swarm_name}] Raw message received: {message}")
                    # Safely decode channel if it's bytes, otherwise use as is
                    channel = message.get('channel', '')
                    if isinstance(channel, bytes):
                        channel = channel.decode('utf-8')
                    logging.info(f"[{self.swarm_name}] Message type: {message.get('type')}, Channel: {channel}")
                    
                    # Handle both subscription and regular messages
                    if message['type'] in ['subscribe', 'message']:
                        try:
                            if message['type'] == 'subscribe':
                                data = {
                                    'type': 'subscription_confirmation',
                                    'channel': channel,
                                    'timestamp': datetime.now().isoformat(),
                                    'swarm': self.swarm_name
                                }
                                logging.info(f"[{self.swarm_name}] Subscription confirmation data: {data}")
                            else:  # message type
                                logging.info(f"[{self.swarm_name}] Attempting to parse message data: {message.get('data')}")
                                data = json.loads(message['data'])
                                logging.info(f"[{self.swarm_name}] Successfully parsed message data")
                                
                            logging.info(f"[{self.swarm_name}] Processing message: {data}")
                            
                            # Check if queue exists
                            queue_length = self.redis_client.llen(self.QUEUES['product_swarm'])
                            logging.info(f"[{self.swarm_name}] Current queue length for {self.QUEUES['product_swarm']}: {queue_length}")
                            
                            # Forward to our own swarm's input queue
                            self.redis_client.rpush(self.QUEUES['product_swarm'], json.dumps(data))

                            # Store queue push event
                            event_data = {
                                "type": "queue_push",
                                "queue": self.QUEUES['product_swarm'],
                                "message_type": data.get('type'),
                                "timestamp": datetime.now().isoformat(),
                                "data": data
                            }
                            await store_agent_event(
                                event_id=f"queue_push_{int(time.time())}",
                                agent_id=f"{self.swarm_name}_manager",
                                event_data=event_data
                            )
                            
                            # Verify message was added
                            new_queue_length = self.redis_client.llen(self.QUEUES['product_swarm'])
                            logging.info(f"[{self.swarm_name}] New queue length: {new_queue_length}")
                            logging.info(f"[{self.swarm_name}] Forwarded message to product swarm queue")
                            
                            # Log queue contents for debugging
                            queue_contents = self.redis_client.lrange(self.QUEUES['product_swarm'], 0, -1)
                            logging.info(f"[{self.swarm_name}] Current queue contents: {queue_contents}")
                            
                        except json.JSONDecodeError as e:
                            logging.error(f"[{self.swarm_name}] Error decoding message data: {e}\nMessage was: {message.get('data')}\nTraceback:\n{traceback.format_exc()}")
                        except Exception as e:
                            logging.error(f"[{self.swarm_name}] Error handling pub/sub message: {e}\nTraceback:\n{traceback.format_exc()}")
            except Exception as e:
                logging.error(f"[{self.swarm_name}] Error in pubsub message handler: {e}\nTraceback:\n{traceback.format_exc()}")
                if not self.running:
                    break
                await asyncio.sleep(1)  # Changed to async sleep

    def stop(self):
        """Stop all workers and cleanup"""
        self.running = False
        logging.info("Stopping all workers...")
        
        # Unsubscribe and close pubsub
        self.pubsub.unsubscribe()
        self.pubsub.close()
        
        # Wait for threads to finish
        for name, thread in self.threads.items():
            logging.info(f"Stopping {name}...")
            thread.join(timeout=5.0)
            if thread.is_alive():
                logging.warning(f"{name} did not stop gracefully")
        
        # Wait for pubsub thread
        self.pubsub_thread.join(timeout=5.0)
        if self.pubsub_thread.is_alive():
            logging.warning("Pub/Sub listener did not stop gracefully")
                
        # Cleanup Redis connection
        if self.redis_client:
            self.redis_client.close()
            
        logging.info("Product Strategy Swarm Manager stopped") 
