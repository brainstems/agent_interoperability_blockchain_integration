import json
import redis
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from promotion_crew import PromotionQueue
import os
from datetime import datetime
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def process_promotion_message(message, redis_client):
    """Process promotion messages and generate store optimization recommendations"""
    try:
        # Notify that processing has started
        redis_client.rpush("api_queue", json.dumps({
            "message": "Marcus Rodriguez is analyzing store performance and generating recommendations...",
            "type": "notification",
            "timestamp": datetime.now().isoformat()
        }))

        # Create promotion crew and generate recommendations
        promotion_crew = PromotionQueue()
        crew = promotion_crew.crew(store_data=message)
        output = crew.kickoff()

        # Log the recommendations
        logging.info("Store optimization recommendations generated: %s", output.raw)
        
        # Publish results to API queue
        redis_client.rpush('api_queue', json.dumps({
            "message": output.raw,
            "type": "promotion_recommendations",
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "analyst": "Marcus Rodriguez",
                "focus_areas": [
                    "Store Layout Optimization",
                    "Content Strategy",
                    "Product Discovery",
                    "Conversion Rate Optimization"
                ]
            }
        }))

        logging.info("Successfully published promotional recommendations")

    except redis.RedisError as e:
        error_trace = traceback.format_exc()
        error_message = f"Redis error while processing promotional message: {str(e)}"
        logging.error(f"{error_message}\n{error_trace}")
        redis_client.rpush('api_queue', json.dumps({
            "message": error_message,
            "type": "error",
            "timestamp": datetime.now().isoformat(),
            "traceback": error_trace
        }))
    except json.JSONDecodeError as e:
        error_trace = traceback.format_exc()
        error_message = f"JSON parsing error in promotional message: {str(e)}"
        logging.error(f"{error_message}\n{error_trace}")
        redis_client.rpush('api_queue', json.dumps({
            "message": error_message,
            "type": "error",
            "timestamp": datetime.now().isoformat(),
            "traceback": error_trace
        }))
    except Exception as e:
        error_trace = traceback.format_exc()
        error_message = f"Unexpected error processing promotional message: {str(e)}"
        logging.error(f"{error_message}\n{error_trace}")
        redis_client.rpush('api_queue', json.dumps({
            "message": error_message,
            "type": "error",
            "timestamp": datetime.now().isoformat(),
            "traceback": error_trace
        }))


def main():
    logging.info("Promotion Execution worker starting...")
    
    # Initialize Redis connection
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    redis_client = redis.from_url(
        url=redis_url,
        decode_responses=True
    )

    try:
        while True:
            try:
                # Wait for messages from the promotion translation queue
                message = redis_client.blpop('promotional_execution_queue', timeout=0)
                
                if message:
                    logging.info("Received store performance data for processing")
                    try:
                        # Parse the message data
                        data = json.loads(message[1])
                        
                        # Process the promotion message
                        process_promotion_message(data, redis_client)
                        
                    except json.JSONDecodeError as e:
                        error_trace = traceback.format_exc()
                        logging.error(f"Error decoding message: {str(e)}\n{error_trace}")
                        continue
                    except Exception as e:
                        error_trace = traceback.format_exc()
                        logging.error(f"Unexpected error processing message: promotion execution {str(e)}\n{error_trace}")
                        continue
                    
            except redis.RedisError as e:
                error_trace = traceback.format_exc()
                logging.error(f"Redis error in main loop: {str(e)}\n{error_trace}")
                # Sleep briefly before retrying
                time.sleep(5)
                continue
                
    except KeyboardInterrupt:
        logging.info("Shutting down promotion execution worker...")
    except Exception as e:
        error_trace = traceback.format_exc()
        logging.error(f"Fatal error in main loop: {str(e)}\n{error_trace}")
    finally:
        redis_client.close()


if __name__ == "__main__":
    main()
