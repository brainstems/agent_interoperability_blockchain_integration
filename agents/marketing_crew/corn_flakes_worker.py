import json
import redis
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from corn_flakes_crew import CornFlakesCrew
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def process_corn_flakes_message(message, redis_client):
    """Process Corn Flakes strategy messages and generate recommendations"""
    try:
        # Notify that processing has started
        redis_client.rpush("api_queue", json.dumps({
            "message": "Classic Corn Flakes specialist is analyzing market data...",
            "type": "notification",
            "timestamp": datetime.now().isoformat()
        }))

        # Create Corn Flakes crew and generate recommendations
        try:
            corn_flakes_crew = CornFlakesCrew()
            crew = corn_flakes_crew.crew(
                current_metrics=message,
                redis_client=redis_client
            )
            output = crew.kickoff()
        except Exception as e:
            error_msg = f"Error in CornFlakesCrew processing: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            raise

        logging.info("Corn Flakes strategy recommendations generated: %s", output.raw)
        
        # Create structured response using the raw output
        try:
            recommendations = json.loads(output.raw)
            strategy_response = {
                "product": "Classic Corn Flakes",
                "timestamp": datetime.now().isoformat(),
                "recommendations": recommendations,
                "metrics": message.get('metrics', {}),
                "region": "Philadelphia",
                "target_demographic": "Households with children aged 5-12"
            }
        except json.JSONDecodeError as e:
            logging.warning(f"JSON parsing failed: {str(e)}\n{traceback.format_exc()}")
            strategy_response = {
                "product": "Classic Corn Flakes",
                "timestamp": datetime.now().isoformat(),
                "recommendations": output.raw,
                "metrics": message.get('metrics', {}),
                "region": "Philadelphia",
                "target_demographic": "Households with children aged 5-12"
            }
        
        # Publish results to queues
        try:
            for queue in ['product_agent_queue', 'api_queue']:
                redis_client.rpush(queue, json.dumps({
                    "message": {
                        "product": "Classic Corn Flakes",
                        "recommendations": strategy_response,
                        "type": "product_strategy",
                    },
                    "type": "corn_flakes_strategy",
                    "timestamp": datetime.now().isoformat()
                }))
        except redis.RedisError as e:
            error_msg = f"Redis publishing error: {str(e)}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            raise

        logging.info("Successfully published Corn Flakes strategy recommendations")

    except Exception as e:
        error_msg = f"Error processing Corn Flakes strategy message: {str(e)}"
        full_traceback = traceback.format_exc()
        logging.error(f"{error_msg}\n{full_traceback}")
        try:
            redis_client.rpush('api_queue', json.dumps({
                "message": error_msg,
                "traceback": full_traceback,
                "type": "error",
                "timestamp": datetime.now().isoformat()
            }))
        except redis.RedisError as redis_err:
            logging.error(f"Failed to publish error message: {str(redis_err)}\n{traceback.format_exc()}")


def main():
    logging.info("Corn Flakes Strategy worker starting...")
    
    # Initialize Redis connection
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    try:
        redis_client = redis.from_url(
            url=redis_url,
            decode_responses=True
        )
    except redis.RedisError as e:
        logging.error(f"Failed to connect to Redis: {str(e)}\n{traceback.format_exc()}")
        return

    try:
        while True:
            try:
                # Wait for messages from the corn flakes strategy queue
                message = redis_client.blpop('corn_flakes_queue', timeout=0)
                
                if message and len(message) == 2:
                    logging.info("Received Corn Flakes strategy request for processing")
                    try:
                        data = json.loads(message[1])
                        process_corn_flakes_message(data, redis_client)
                    except json.JSONDecodeError as e:
                        logging.error(f"Error decoding message: {str(e)}\n{traceback.format_exc()}")
                        continue
                    except Exception as e:
                        logging.error(f"Unexpected error processing message: corn flask {str(e)}\n{traceback.format_exc()}") 
                        continue
                else:
                    logging.warning("Received invalid message format from Redis")
                    continue
                    
            except redis.RedisError as e:
                logging.error(f"Redis operation error: {str(e)}\n{traceback.format_exc()}")
                continue
                
    except KeyboardInterrupt:
        logging.info("Shutting down Corn Flakes strategy worker...")
    except Exception as e:
        logging.error(f"Critical error in main loop: {str(e)}\n{traceback.format_exc()}")
    finally:
        try:
            redis_client.close()
        except Exception as e:
            logging.error(f"Error closing Redis connection: {str(e)}\n{traceback.format_exc()}")


if __name__ == "__main__":
    main()
