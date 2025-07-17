import json
import os
import redis
import logging
import traceback
import time
from typing import Optional, Dict, Any, Union
from concurrent.futures import ThreadPoolExecutor
from ..translation_crew.translation_crew import SalesToInventoryTranslationCrew

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class InventoryTranslationWorker:
    """Worker for handling inventory translation tasks."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize the inventory translation worker.
        
        Args:
            redis_client: Optional Redis client instance. If not provided, a new one will be created.
        """
        self.redis_client = redis_client or redis.Redis(host='localhost', port=6379, db=0)
    
    def process_message(self, message: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Process an incoming message through the inventory translation pipeline.
        
        Args:
            message: The message to process (can be JSON string or dict)
            
        Returns:
            Dict containing the processing result
        """
        try:
            # Parse message if it's a JSON string
            if isinstance(message, str):
                try:
                    message = json.loads(message)
                except json.JSONDecodeError:
                    error_msg = "Failed to decode message as JSON"
                    logging.error(error_msg)
                    return self._handle_error(error_msg, traceback.format_exc())
            
            # Log that we're starting to process
            self.redis_client.rpush("api_queue", json.dumps({
                "message": "Inventory translation worker is thinking...",
                "type": "notification"
            }))
            
            # Process the message using the translation crew
            crew = SalesToInventoryTranslationCrew().crew(original_message=message)
            output = crew.kickoff()
            logging.info("Inventory translation output: %s", output.raw)
            
            # Prepare success result
            result = {
                "message": output.raw,
                "type": "inventory_translation",
                "status": "success"
            }
            
            # Publish to the next queue
            try:
                self.redis_client.rpush('api_queue', json.dumps(result))
                self.redis_client.rpush('inventory_execution_queue', json.dumps({
                    **result,
                    "type": "inventory_translation_queue"
                }))
                logging.info("Successfully published to api queue")
            except redis.RedisError as e:
                raise RuntimeError(f"Failed to publish to Redis: {str(e)}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logging.error(error_msg)
            logging.error(traceback.format_exc())
            return self._handle_error(error_msg, traceback.format_exc())
    
    def _handle_error(self, error_msg: str, traceback_str: str) -> Dict[str, Any]:
        """Handle errors consistently.
        
        Args:
            error_msg: Error message
            traceback_str: Formatted traceback string
            
        Returns:
            Error result dictionary
        """
        error_result = {
            "error": error_msg,
            "type": "error",
            "traceback": traceback_str,
            "status": "error"
        }
        
        try:
            self.redis_client.rpush('error_queue', json.dumps(error_result))
        except:
            logging.error("Failed to publish error to error queue")
            
        return error_result


def process_message(message: Union[str, Dict[str, Any]], redis_client: redis.Redis) -> Dict[str, Any]:
    """Legacy function to maintain backward compatibility.
    
    Args:
        message: The message to process (can be JSON string or dict)
        redis_client: Redis client instance
        
    Returns:
        Dict containing the processing result
    """
    worker = InventoryTranslationWorker(redis_client)
    return worker.process_message(message)


def main():
    """Main entry point for the inventory translation worker."""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    redis_client = None
    
    try:
        # Create Redis client with connection pooling
        redis_client = redis.from_url(
            url=redis_url,
            decode_responses=False,  # Keep as bytes for consistency
            socket_connect_timeout=5,
            socket_keepalive=True,
            retry_on_timeout=True
        )
        
        # Test the connection
        redis_client.ping()
        
        worker = InventoryTranslationWorker(redis_client)
        logging.info("Starting inventory translation worker...")
        
        # Use ThreadPoolExecutor to handle multiple messages concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            while True:
                try:
                    # Blocking pop from the queue with a timeout to allow for graceful shutdown
                    message_data = redis_client.blpop('inventory_translation_queue', timeout=1)
                    
                    if message_data is None:
                        # Timeout reached, continue the loop to check for shutdown
                        continue
                        
                    _, message_json = message_data
                    logging.info("Received message from inventory translation queue")
                    
                    # Submit the message processing to the thread pool
                    executor.submit(worker.process_message, message_json)
                    
                except redis.RedisError as e:
                    logging.error(f"Redis error: {str(e)}")
                    logging.error(traceback.format_exc())
                    time.sleep(5)  # Wait before retrying
                    
                except KeyboardInterrupt:
                    logging.info("Shutting down worker...")
                    break
                    
                except Exception as e:
                    logging.error(f"Unexpected error: {str(e)}")
                    logging.error(traceback.format_exc())
                    time.sleep(1)  # Prevent tight loop on unexpected errors
    
    except Exception as e:
        logging.error(f"Fatal error in inventory translation worker: {str(e)}")
        logging.error(traceback.format_exc())
    finally:
        if redis_client:
            try:
                redis_client.close()
            except:
                pass  # Best effort cleanup


if __name__ == "__main__":
    main()
