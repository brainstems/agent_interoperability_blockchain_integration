import json
import redis
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from inventory_crew import InventoryCrew
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def process_inventory_message(message, redis_client):
    """Process inventory messages and generate recommendations"""
    try:
        # Notify that processing has started
        redis_client.rpush("api_queue", json.dumps({
            "message": "Inventory crew is analyzing data and generating recommendations...",
            "type": "notification",
            "timestamp": datetime.now().isoformat()
        }))

        # Create inventory crew and generate recommendations
        inventory_crew = InventoryCrew()
        crew = inventory_crew.crew(inventory_data=message)
        output = crew.kickoff()

        # Log the recommendations
        logging.info("Inventory recommendations generated: %s", output.raw)
        
        try:
            redis_client.rpush('api_queue', json.dumps({
                "message": output.raw,
                "type": "inventory_recommendations",
                "timestamp": datetime.now().isoformat()
            }))
        except (redis.RedisError, json.JSONDecodeError) as e:
            error_msg = f"Failed to publish recommendations: {str(e)}\nTraceback:\n{traceback.format_exc()}"
            logging.error(error_msg)
            raise

        logging.info("Successfully published inventory recommendations")

    except Exception as e:
        error_msg = f"Error processing inventory message: {str(e)}\nTraceback:\n{traceback.format_exc()}"
        logging.error(error_msg)
        try:
            redis_client.rpush('api_queue', json.dumps({
                "message": error_msg,
                "type": "error",
                "timestamp": datetime.now().isoformat()
            }))
        except Exception as pub_error:
            logging.error(f"Failed to publish error message: {str(pub_error)}\nTraceback:\n{traceback.format_exc()}")


def main():
    logging.info("Inventory Execution worker starting...")
    
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        redis_client = redis.from_url(
            url=redis_url,
            decode_responses=True
        )
    except redis.RedisError as e:
        logging.error(f"Failed to connect to Redis: {str(e)}\nTraceback:\n{traceback.format_exc()}")
        return

    try:
        while True:
            try:
                message = redis_client.blpop('inventory_execution_queue', timeout=0)
                
                if message and len(message) == 2:
                    logging.info("Received inventory data for processing")
                    try:
                        data = json.loads(message[1])
                        process_inventory_message(data, redis_client)
                    except json.JSONDecodeError as e:
                        error_msg = f"Error decoding message: {str(e)}\nTraceback:\n{traceback.format_exc()}"
                        logging.error(error_msg)
                        continue
                    except Exception as e:
                        error_msg = f"Unexpected error processing message: inventory execution {str(e)}\nTraceback:\n{traceback.format_exc()}"
                        logging.error(error_msg)
                        continue
                else:
                    logging.warning("Received invalid message format from Redis")
                    continue
                    
            except redis.RedisError as e:
                error_msg = f"Redis operation error: {str(e)}\nTraceback:\n{traceback.format_exc()}"
                logging.error(error_msg)
                continue
                
    except KeyboardInterrupt:
        logging.info("Shutting down inventory execution worker...")
    except Exception as e:
        logging.error(f"Critical error in main loop: {str(e)}\nTraceback:\n{traceback.format_exc()}")
    finally:
        try:
            redis_client.close()
        except Exception as e:
            logging.error(f"Error closing Redis connection: {str(e)}\nTraceback:\n{traceback.format_exc()}")


if __name__ == "__main__":
    main() 
