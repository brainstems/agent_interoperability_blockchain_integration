import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

import redis.asyncio as redis
from pydantic import ValidationError

from agents.infrastructure.schemas.contract_net_schemas import (
    CFPMessage,
    BidMessage,
    AwardMessage,
    TaskResultMessage,
    CFP_BROADCAST_CHANNEL,
    TASK_RESULT_QUEUE_PATTERN, # Used by orchestrator, worker gets it in award
    # Need a pattern for worker award queues
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

WORKER_AWARD_QUEUE_PATTERN = "worker:{worker_id}:awards"

class BasicWorkerAgent:
    def __init__(self, agent_id: Optional[str] = None, redis_host: str = 'localhost', redis_port: int = 6379):
        self.agent_id = agent_id or f"worker-{uuid.uuid4()}"
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_pool: Optional[redis.Redis] = None
        self.pubsub_client: Optional[redis.client.PubSub] = None
        self.is_running = False
        self._tasks: List[asyncio.Task] = []
        self.award_notification_queue = WORKER_AWARD_QUEUE_PATTERN.format(worker_id=self.agent_id)

    async def _connect_redis(self):
        if not self.redis_pool:
            try:
                self.redis_pool = redis.Redis(host=self.redis_host, port=self.redis_port, auto_close_connection_pool=False)
                await self.redis_pool.ping()
                logger.info(f"[{self.agent_id}] Connected to Redis at {self.redis_host}:{self.redis_port}")
            except Exception as e:
                logger.error(f"[{self.agent_id}] Failed to connect to Redis: {e}")
                self.redis_pool = None # Ensure it's None if connection failed
                raise

    async def _handle_cfp_message(self, message_data: str):
        try:
            cfp_data = json.loads(message_data)
            # Basic check for task_id before full Pydantic validation
            if "task_id" not in cfp_data:
                logger.warning(f"[{self.agent_id}] Received CFP message without task_id. Discarding: {message_data[:100]}")
                return
            
            cfp = CFPMessage(**cfp_data)
            logger.info(f"[{self.agent_id}] Received CFP for task {cfp.task_id}: {cfp.task_description}")

            # Simple bidding logic: bid on 50% of tasks with a random cost
            if random.random() < 0.8: # Increased probability to ensure more bids for testing
                cost_bid = round(random.uniform(5.0, 50.0), 2)
                bid_details = {
                    "estimated_duration_seconds": round(random.uniform(10, 120), 1),
                    "cost_bid_units": cost_bid,
                    "worker_current_load": round(random.random(), 2) # 0.0 to 1.0
                }
                bid_message = BidMessage(
                    task_id=cfp.task_id,
                    bidder_id=self.agent_id,
                    bid_details=bid_details,
                    award_notification_queue=self.award_notification_queue
                )
                if self.redis_pool:
                    await self.redis_pool.rpush(cfp.bid_submission_queue, bid_message.json())
                    logger.info(f"[{self.agent_id}] Submitted bid for task {cfp.task_id} to {cfp.bid_submission_queue} with cost {cost_bid}.")
                else:
                    logger.error(f"[{self.agent_id}] Cannot submit bid for task {cfp.task_id}, Redis not connected.")
            else:
                logger.info(f"[{self.agent_id}] Decided not to bid on task {cfp.task_id}.")

        except json.JSONDecodeError:
            logger.error(f"[{self.agent_id}] Failed to decode CFP JSON: {message_data[:200]}")
        except ValidationError as e:
            logger.error(f"[{self.agent_id}] Invalid CFP message structure: {e.errors()} for data: {message_data[:200]}")
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error processing CFP message for task {cfp_data.get('task_id', 'UNKNOWN_TASK') if 'cfp_data' in locals() else 'UNKNOWN_TASK'}: {e}", exc_info=True)

    async def _listen_for_cfps(self):
        if not self.redis_pool:
            logger.error(f"[{self.agent_id}] Cannot listen for CFPs, Redis not connected.")
            return
        
        self.pubsub_client = self.redis_pool.pubsub()
        try:
            await self.pubsub_client.subscribe(CFP_BROADCAST_CHANNEL)
            logger.info(f"[{self.agent_id}] Subscribed to CFP broadcast channel: {CFP_BROADCAST_CHANNEL}")
            while self.is_running:
                try:
                    message = await self.pubsub_client.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message['type'] == 'message':
                        await self._handle_cfp_message(message['data'].decode('utf-8'))
                    await asyncio.sleep(0.01) # Yield control briefly
                except redis.exceptions.ConnectionError as e:
                    logger.error(f"[{self.agent_id}] Redis connection error while listening for CFPs: {e}. Attempting to reconnect...")
                    await self._connect_redis() # Try to reconnect
                    if self.redis_pool: # Re-subscribe if connection re-established
                        self.pubsub_client = self.redis_pool.pubsub()
                        await self.pubsub_client.subscribe(CFP_BROADCAST_CHANNEL)
                    else:
                        await asyncio.sleep(5) # Wait before retrying connection
                except asyncio.CancelledError:
                    logger.info(f"[{self.agent_id}] CFP listener cancelled.")
                    break
                except Exception as e:
                    logger.error(f"[{self.agent_id}] Unexpected error in CFP listener: {e}", exc_info=True)
                    await asyncio.sleep(1) # Avoid rapid error looping
        finally:
            if self.pubsub_client:
                try:
                    await self.pubsub_client.unsubscribe(CFP_BROADCAST_CHANNEL)
                    await self.pubsub_client.close()
                    logger.info(f"[{self.agent_id}] Unsubscribed from {CFP_BROADCAST_CHANNEL} and closed pubsub client.")
                except Exception as e:
                    logger.error(f"[{self.agent_id}] Error closing pubsub client: {e}")
            self.pubsub_client = None

    async def _execute_task(self, award: AwardMessage):
        logger.info(f"[{self.agent_id}] Starting execution for awarded task {award.task_id}: {award.task_details}")
        await asyncio.sleep(random.uniform(2, 7)) # Simulate work

        # Simulate success or failure
        success = random.random() < 0.9 # 90% success rate
        result_data: Optional[Dict[str, Any]] = None
        error_message: Optional[str] = None

        if success:
            result_data = {"output": f"Task {award.task_id} completed successfully by {self.agent_id}", "value": random.randint(1,100)}
            logger.info(f"[{self.agent_id}] Task {award.task_id} completed successfully.")
        else:
            error_message = f"Task {award.task_id} failed during execution by {self.agent_id}. Simulated error."
            logger.warning(f"[{self.agent_id}] Task {award.task_id} failed.")

        result_message = TaskResultMessage(
            task_id=award.task_id,
            worker_id=self.agent_id,
            success=success,
            result_data=result_data,
            error_message=error_message,
            completed_at=datetime.now(timezone.utc)
        )

        if self.redis_pool:
            try:
                await self.redis_pool.rpush(award.result_submission_queue, result_message.json())
                logger.info(f"[{self.agent_id}] Sent result for task {award.task_id} to {award.result_submission_queue}.")
            except Exception as e:
                logger.error(f"[{self.agent_id}] Failed to send result for task {award.task_id} to {award.result_submission_queue}: {e}")
        else:
            logger.error(f"[{self.agent_id}] Cannot send task result for {award.task_id}, Redis not connected.")

    async def _listen_for_awards(self):
        if not self.redis_pool:
            logger.error(f"[{self.agent_id}] Cannot listen for awards, Redis not connected.")
            return

        logger.info(f"[{self.agent_id}] Listening for awards on {self.award_notification_queue}")
        while self.is_running:
            try:
                # BLPOP returns a tuple (queue_name, value) or None if timeout
                message_tuple = await self.redis_pool.blpop([self.award_notification_queue], timeout=1)
                if message_tuple:
                    _queue, message_data_bytes = message_tuple
                    message_data = message_data_bytes.decode('utf-8')
                    try:
                        award_data = json.loads(message_data)
                        if award_data.get("task_id") is None or award_data.get("winning_bidder_id") != self.agent_id:
                            logger.warning(f"[{self.agent_id}] Received award message not for this agent or missing task_id. Discarding. Data: {message_data[:100]}")
                            continue
                        award = AwardMessage(**award_data)
                        logger.info(f"[{self.agent_id}] Received award for task {award.task_id}.")
                        # Don't wait for task execution, schedule it
                        asyncio.create_task(self._execute_task(award))
                    except json.JSONDecodeError:
                        logger.error(f"[{self.agent_id}] Failed to decode award JSON: {message_data[:200]}")
                    except ValidationError as e:
                        logger.error(f"[{self.agent_id}] Invalid award message structure: {e.errors()} for data: {message_data[:200]}")
                    except Exception as e:
                        logger.error(f"[{self.agent_id}] Error processing award message: {e}", exc_info=True)
                await asyncio.sleep(0.01) # Yield control briefly
            except redis.exceptions.ConnectionError as e:
                logger.error(f"[{self.agent_id}] Redis connection error while listening for awards: {e}. Attempting to reconnect...")
                await self._connect_redis()
                if not self.redis_pool:
                    await asyncio.sleep(5) # Wait before retrying connection
            except asyncio.CancelledError:
                logger.info(f"[{self.agent_id}] Award listener cancelled.")
                break
            except Exception as e:
                logger.error(f"[{self.agent_id}] Unexpected error in award listener: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def start(self):
        if self.is_running:
            logger.warning(f"[{self.agent_id}] Agent already running.")
            return
        self.is_running = True
        try:
            await self._connect_redis()
            if not self.redis_pool: # If connection failed in _connect_redis
                self.is_running = False
                logger.error(f"[{self.agent_id}] Could not start agent due to Redis connection failure.")
                return
        except Exception as e:
            self.is_running = False
            logger.error(f"[{self.agent_id}] Critical error during Redis connection on start: {e}")
            return

        logger.info(f"[{self.agent_id}] Starting BasicWorkerAgent...")
        self._tasks.append(asyncio.create_task(self._listen_for_cfps()))
        self._tasks.append(asyncio.create_task(self._listen_for_awards()))
        logger.info(f"[{self.agent_id}] Agent started with {len(self._tasks)} background tasks.")

    async def stop(self):
        if not self.is_running and not self._tasks:
            logger.info(f"[{self.agent_id}] Agent already stopped or was not started.")
            return
            
        logger.info(f"[{self.agent_id}] Stopping BasicWorkerAgent...")
        self.is_running = False # Signal loops to stop

        # Cancel all running asyncio tasks
        cancelled_tasks = []
        for task in self._tasks:
            if not task.done():
                task.cancel()
                cancelled_tasks.append(task)
        
        if cancelled_tasks:
            await asyncio.gather(*cancelled_tasks, return_exceptions=True)
            logger.info(f"[{self.agent_id}] Cancelled {len(cancelled_tasks)} background tasks.")
        self._tasks = []

        if self.pubsub_client: # Ensure pubsub client is closed if it was created
            try:
                await self.pubsub_client.unsubscribe()
                await self.pubsub_client.close()
                logger.info(f"[{self.agent_id}] Pubsub client closed during stop.")
            except Exception as e:
                logger.error(f"[{self.agent_id}] Error closing pubsub client during stop: {e}")
            self.pubsub_client = None

        if self.redis_pool:
            try:
                await self.redis_pool.close()
                await self.redis_pool.connection_pool.disconnect()
                logger.info(f"[{self.agent_id}] Redis connection pool closed.")
            except Exception as e:
                logger.error(f"[{self.agent_id}] Error closing Redis connection pool: {e}")
            self.redis_pool = None
        logger.info(f"[{self.agent_id}] Agent stopped.")

# Example usage (for testing purposes)
async def main():
    # Create a few worker agents
    num_workers = 3
    workers: List[BasicWorkerAgent] = []
    for i in range(num_workers):
        worker = BasicWorkerAgent(agent_id=f"worker-alpha-{i}")
        workers.append(worker)
        await worker.start()

    try:
        # Keep them running for a while
        await asyncio.sleep(60) # Let workers run for 60 seconds
    except asyncio.CancelledError:
        logger.info("Main task cancelled, stopping workers.")
    finally:
        logger.info("Shutting down workers...")
        for worker in workers:
            await worker.stop()
        logger.info("All workers stopped.")

if __name__ == "__main__":
    # Need to import random for the example logic
    import random
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down.")
