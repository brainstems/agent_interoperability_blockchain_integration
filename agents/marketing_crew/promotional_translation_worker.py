import json
import redis
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from infrastructure_crew.translation_crew import SalesToPromotionalTranslationCrew

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_message(message, redis_client):
    try:
        redis_client.rpush("api_queue", json.dumps({
            "message": "Promotional translation worker is thinking...",
            "type": "notification"
        }))
        crew = SalesToPromotionalTranslationCrew().crew(original_message=message)
        output = crew.kickoff()
        logging.info("Promotional translation output: %s", output.raw)
        
        # Publish to the next queue
        try:
            # Also publish to api queue for UI
            redis_client.rpush('api_queue', json.dumps({
                "message": output.raw,
                "type": "promotional_translation"
            }))

            redis_client.rpush('promotional_execution_queue', json.dumps({
                "message": output.raw,
                "type": "promotional_execution_queue"
            }))
            logging.info("Successfully published to api queue")
        except redis.RedisError as e:
            error_message = f"Redis error while publishing to queue: {str(e)}\nTraceback:\n{traceback.format_exc()}"
            logging.error(error_message)
            redis_client.rpush("api_queue", json.dumps({
                "message": error_message,
                "type": "error"
            }))
    except Exception as e:
        error_message = f"Error in process_message: {str(e)}\nTraceback:\n{traceback.format_exc()}"
        logging.error(error_message)
        try:
            redis_client.rpush("api_queue", json.dumps({
                "message": error_message,
                "type": "error"
            }))
        except:
            logging.error("Failed to send error to api_queue: %s", traceback.format_exc())

def main():
    logging.info("Promotional Translation worker starting...")
    
    redis_url = 'redis://default:z0wGFr1Q9X6TUjOMiMcL4AeG6a6G116Q@redis-18224.c10.us-east-1-4.ec2.redns.redis-cloud.com:18224'
    redis_client = redis.from_url(
        url=redis_url,
        decode_responses=True
    )

    try:
        while True:
            try:
                message = redis_client.blpop('promotional_translation_queue', timeout=0)
                if message:
                    logging.info("Received message from promotional queue")
                    try:
                        data = json.loads(message[1])
                        process_message(data, redis_client)
                    except json.JSONDecodeError as e:
                        error_message = f"JSON decode error: {str(e)}\nTraceback:\n{traceback.format_exc()}"
                        logging.error(error_message)
                        redis_client.rpush("api_queue", json.dumps({
                            "message": error_message,
                            "type": "error"
                        }))
                        continue
            except redis.RedisError as e:
                error_message = f"Redis error in main loop: {str(e)}\nTraceback:\n{traceback.format_exc()}"
                logging.error(error_message)
                continue
                    
    except KeyboardInterrupt:
        logging.info("Shutting down promotional translation worker...")
    except Exception as e:
        error_message = f"Unexpected error in main loop: {str(e)}\nTraceback:\n{traceback.format_exc()}"
        logging.error(error_message)
    finally:
        redis_client.close()

if __name__ == "__main__":
    main()