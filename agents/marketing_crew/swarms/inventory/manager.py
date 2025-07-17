import threading
from concurrent.futures import ThreadPoolExecutor
from swarms.common.common import (
    logging,
    get_redis_client,
    handle_worker_error,
)
from swarms.inventory.worker import InventoryWorker, OptimizationWorker
from swarms.inventory.leader import Leader
from swarms.inventory.translator import TranslationWorker
from swarms.inventory.consensus import ConsensusWorker
import json
from swarms.common.api import store_agent_state, store_agent_event
import time
import traceback
from datetime import datetime
import asyncio
from swarms.memory.swarm import SwarmMemoryAgent
from swarms.memory.agent import EntityState


class InventorySwarmManager:
    """Manager class to orchestrate all inventory swarm components"""
    
    # Queue configuration
    QUEUES = {
        'inventory_swarm': 'inventory-swarm',
        'shared_channel': 'state-swarm',  # Update shared pub/sub channel
        'translation': 'inventory-translator',
        'worker': 'inventory-worker-queue',
        'consensus': 'inventory-consensus',
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
        self.worker_names = ['inventory_worker', 'optimization_worker']
        # Add callback methods
        self.callbacks = {
            'leader': self.leader_callback,
            'translation': self.translation_callback,
            'consensus': self.consensus_callback,
            'worker': self.worker_callback
        }
        
    # Add callback methods
    async def leader_callback(self, data):
        logging.info(f"Leader output: {data}")
        
        # Push to API queue
        api_message = {
            "message": data,
            "swarm_name": self.swarm_name,
            "type": f"{self.swarm_name}_leader"
        }
        self.redis_client.rpush(self.QUEUES['api_query'], json.dumps(api_message))

        # Store queue push event
        event_data = {
            "type": "queue_push",
            "queue": self.QUEUES['api_query'],
            "message_type": "leader_output",
            "timestamp": datetime.now().isoformat(),
            "swarm_name": self.swarm_name,
            "data": api_message
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
            "data": data
        }
        await store_agent_event(
            event_id=f"leader_{int(time.time())}",
            agent_id=f"{self.swarm_name}_leader",
            event_data=event_data
        )
        
        state_data = {
            "agentId": f"{self.swarm_name}_leader",
            "memoryType": "inventory_swarm_leader_state",
            "attributes": data
        }
        try:
            result = await store_agent_state("leader", state_data)
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
                "data": data
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
            "memoryType": "inventory_swarm_translation_state",
            "attributes": data
        }
        try:
            result = await store_agent_state("translator", state_data)
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
        
        # Store event in external API
        try:
            event_data = {
                "type": "consensus_output",
                "worker": self.swarm_name,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            await store_agent_event(
                event_id=f"consensus_{int(time.time())}",
                agent_id=f"{self.swarm_name}_consensus",
                event_data=event_data
            )
            logging.info("Consensus event stored successfully")
        except Exception as e:
            logging.error(f"Failed to store consensus event: {str(e)}\nTraceback:\n{traceback.format_exc()}")
        
        # Create SwarmMemoryAgent instance
        swarm_memory = SwarmMemoryAgent(
            swarm_id=self.swarm_name,
            storage_dir=f"swarm_memories/{self.swarm_name}"
        )
        
        # Extract input data and outcome from consensus data
        input_data = {
            "worker_outputs": data.get("worker_outputs", {}),
            "worker_count": data.get("worker_count", 0),
            "timestamp": datetime.now().isoformat()
        }
        
        outcome = {
            "consensus_result": data.get("consensus_result", {}),
            "agreement_level": data.get("agreement_level", 0),
            "final_decision": data.get("final_decision", {})
        }
        
        # Create entities from worker data
        entities = [
            EntityState(
                entity_id=worker_id,
                entity_type="worker",
                attributes=worker_output
            )
            for worker_id, worker_output in data.get("worker_outputs", {}).items()
        ]
        
        # Store memory if it passes importance threshold
        memory = swarm_memory.create_memory(
            memory_id=f"consensus_{int(time.time())}",
            input_data=input_data,
            outcome=outcome,
            agent_state={
                "swarm_name": self.swarm_name,
                "consensus_timestamp": datetime.now().isoformat(),
                "consensus_status": "completed"
            },
            entities=entities
        )
        
        if memory:
            logging.info(f"Stored consensus memory: {memory.memory_id}")
        else:
            logging.info("Consensus memory did not meet importance threshold")
        
        state_data = {
            "agentId": f"{self.swarm_name}_consensus",
            "memoryType": "inventory_swarm_consensus_state",
            "attributes": data
        }
        try:
            result = await store_agent_state("consensus", state_data)
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
        
        # Store event in external API
        try:
            worker_id = data.get("worker_id", "worker")
            event_data = {
                "type": "worker_output",
                "worker": self.swarm_name,
                "worker_id": worker_id,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            await store_agent_event(
                event_id=f"worker_{worker_id}_{int(time.time())}",
                agent_id=f"{self.swarm_name}_worker",
                event_data=event_data
            )
            logging.info("Worker event stored successfully")
        except Exception as e:
            logging.error(f"Failed to store worker event: {str(e)}\nTraceback:\n{traceback.format_exc()}")
        
        worker_id = data.get("worker_id", "worker")
        state_data = {
            "agentId": f"{self.swarm_name}_worker",
            "memoryType": "inventory_swarm_worker_state",
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
            
            # Set running to True before starting threads
            self.running = True
            logging.info(f"[{self.swarm_name}] Set running status to: {self.running}")
            
            # Start pubsub listener thread
            self.pubsub_thread = threading.Thread(
                target=lambda: asyncio.run(self.handle_pubsub_messages()),
                name=f"{self.swarm_name}_pubsub_listener",
                daemon=True
            )
            self.pubsub_thread.start()
            logging.info(f"[{self.swarm_name}] Started pubsub listener thread")
            
            logging.info(f"[{self.swarm_name}] Inventory Swarm Manager initializing...")
            
            # Initialize base components with callbacks
            self.workers = {
                'leader': Leader(
                    input_queue=self.QUEUES['inventory_swarm'],
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
                    output_queue=self.QUEUES['inventory_swarm'],
                    callback=self.callbacks['consensus'],
                    worker_names=self.worker_names,
                    swarm_name=self.swarm_name
                )
            }
            
            # Initialize workers
            self.workers['inventory_worker'] = InventoryWorker(
                worker_name='inventory_worker',
                input_queue=self.QUEUES['worker'],
                output_queue=self.QUEUES['consensus'],
                callback=self.callbacks['worker']
            )
            
            self.workers['optimization_worker'] = OptimizationWorker(
                worker_name='optimization_worker',
                input_queue=self.QUEUES['worker'],
                output_queue=self.QUEUES['consensus'],
                callback=self.callbacks['worker']
            )
            
            # Log queue configuration
            logging.info("Queue Configuration:")
            for worker_name, worker in self.workers.items():
                logging.info(f"{worker_name}: {worker.input_queue} -> {worker.output_queue}")
            
        except Exception as e:
            logging.error(f"Failed to initialize Inventory Swarm Manager: {str(e)}\nTraceback:\n{traceback.format_exc()}")
            raise
            
    async def handle_pubsub_messages(self):
        """Handle messages from the shared pub/sub channel"""
        logging.info(f"[{self.swarm_name}] Starting pubsub message handler")
        logging.info(f"[{self.swarm_name}] Running status: {self.running}")
        
        while self.running:
            try:
                message = self.pubsub.get_message(timeout=1.0)
                
                if message:
                    logging.info(f"[{self.swarm_name}] Raw message received: {message}")
                    
                    # Handle channel decoding for both bytes and string types
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
                            queue_length = self.redis_client.llen(self.QUEUES['inventory_swarm'])
                            logging.info(f"[{self.swarm_name}] Current queue length for {self.QUEUES['inventory_swarm']}: {queue_length}")
                            
                            # Forward to our own swarm's input queue
                            self.redis_client.rpush(self.QUEUES['inventory_swarm'], json.dumps(data))

                            # Store queue push event - now properly awaited
                            event_data = {
                                "type": "queue_push",
                                "queue": self.QUEUES['inventory_swarm'],
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
                            new_queue_length = self.redis_client.llen(self.QUEUES['inventory_swarm'])
                            logging.info(f"[{self.swarm_name}] New queue length: {new_queue_length}")
                            logging.info(f"[{self.swarm_name}] Forwarded message to inventory swarm queue")
                            
                            # Log queue contents for debugging
                            queue_contents = self.redis_client.lrange(self.QUEUES['inventory_swarm'], 0, -1)
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
                'inventory_worker', 'optimization_worker',  # Start all workers
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
            
        logging.info("Inventory Swarm Manager stopped")
