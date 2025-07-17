import json
import redis
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from simulation_crew import SimulationCrew
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def process_message(message, redis_client, current_metrics_channels):
    try:
        # Randomly choose expected outcome
        expected_outcome = random.choice(["positive", "negative"])
        
        redis_client.rpush("api_queue", json.dumps({
            "message": "Simulation worker is thinking for outcome: " + expected_outcome,
            "type": "notification"
        }))

        crew = SimulationCrew().crew(
            simulation_input=message,
            current_metrics=current_metrics_channels,
            expected_outcome=expected_outcome
        )
        output = crew.kickoff()
        logging.info("Simulation output: %s", output.raw)
        
        # Publish final results
        try:
            redis_client.rpush('results_queue', json.dumps(output.raw))
            logging.info("Successfully published simulation results")
            # Updated API queue payload to include expected_outcome
            redis_client.rpush('api_queue', json.dumps({
                "message": output.raw,
                "type": "simulation",
                "expected_outcome": expected_outcome
            }))
            logging.info("Successfully published to api queue")
        except redis.RedisError as e:
            error_traceback = traceback.format_exc()
            logging.error("Error publishing results: %s\nTraceback:\n%s", str(e), error_traceback)
            redis_client.rpush('api_queue', json.dumps({
                "message": f"Error in simulation worker: {str(e)}",
                "type": "error",
                "traceback": error_traceback
            }))
    except Exception as e:
        error_traceback = traceback.format_exc()
        logging.error("Error processing message: simulation worker %s\nTraceback:\n%s", str(e), error_traceback)
        redis_client.rpush('api_queue', json.dumps({
            "message": f"Error in simulation worker: {str(e)}",
            "type": "error",
            "traceback": error_traceback
        }))


def main():
    logging.info("Simulation worker starting...")
    
    try:
        redis_url = 'redis://default:z0wGFr1Q9X6TUjOMiMcL4AeG6a6G116Q@redis-18224.c10.us-east-1-4.ec2.redns.redis-cloud.com:18224'
        redis_client = redis.from_url(
            url=redis_url,
            decode_responses=True
        )

        # You'll need to define current_metrics_channels here or load it from configuration
        current_metrics_channels = {}  # Define your metrics here

        while True:
            try:
                message = redis_client.blpop('simulation_queue', timeout=0)
                if message:
                    logging.info("Received message from simulation queue")
                    data = json.loads(message[1])
                    
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        executor.submit(process_message, data, redis_client, current_metrics_channels)
            except redis.RedisError as e:
                error_traceback = traceback.format_exc()
                logging.error("Redis error in main loop: %s\nTraceback:\n%s", str(e), error_traceback)
                continue
            except json.JSONDecodeError as e:
                error_traceback = traceback.format_exc()
                logging.error("JSON decode error: %s\nTraceback:\n%s", str(e), error_traceback)
                continue
            except Exception as e:
                error_traceback = traceback.format_exc()
                logging.error("Unexpected error in main loop: %s\nTraceback:\n%s", str(e), error_traceback)
                continue
                    
    except KeyboardInterrupt:
        logging.info("Shutting down simulation worker...")
    except Exception as e:
        error_traceback = traceback.format_exc()
        logging.error("Fatal error in main: %s\nTraceback:\n%s", str(e), error_traceback)
    finally:
        redis_client.close()


if __name__ == "__main__":
    main()
