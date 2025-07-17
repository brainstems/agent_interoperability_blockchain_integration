#!/usr/bin/env python
import json
import redis
import time
from typing import Optional, Dict, Any
from sarah import MarketingCrew
import logging


class QueueWorker:

    def __init__(self):
        redis_url = 'redis://default:z0wGFr1Q9X6TUjOMiMcL4AeG6a6G116Q@redis-18224.c10.us-east-1-4.ec2.redns.redis-cloud.com:18224'
        self.redis_client = redis.from_url(
            url=redis_url,
            decode_responses=True
        )
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def process_marketing_message(self, message: Dict[str, Any]) -> None:
        """Process marketing message logic here"""
        logging.info(f"Processing marketing message: {message}")
        # Add your marketing processing logic here
        
        self.redis_client.rpush('api_queue', json.dumps({
          "message": f"Starting marketing {message}",
          "type": "marketing"
        }))
        
        max_retries = 3
        attempt = 0
        is_valid = False
        rule_logs = ""  

        crew = MarketingCrew().crew()

        while attempt < max_retries and not is_valid:
          logging.info(f"Attempt: {attempt}")
          crew_message = message.get('campaign', {})
          if "business_context" not in crew_message:
            crew_message["business_context"] = ""

          logging.info(f"Business Context: {crew_message.get('business_context', '')}")
          crew_output = crew.kickoff(inputs=crew_message)
          # Accessing the crew output
          logging.info(f"Raw Output: {crew_output.raw}")

          self.redis_client.rpush('api_queue', json.dumps({
            "message": crew_output.raw,
            "type": "marketing"
          }))

          marketing_output = json.loads(crew_output.raw)
          rule_enforcement_layer = MarketingRuleEnforcementLayer()
          is_valid, rule_logs = rule_enforcement_layer.validate_output(marketing_output.get('budget_required', {}), "budget_required")

          logging.info(f"Is Valid: {is_valid}")
          if not is_valid:
              logging.error(f"Marketing crew output failed rule validation: {rule_logs}")
              self.redis_client.rpush('api_queue', json.dumps({
                "message": f"Marketing crew output failed rule validation: {rule_logs} Attempt: {attempt}",
                "type": "error"
              }))
              # Update business context with rule logs for retry
              crew_message["business_context"] = f"Important Business Context: {rule_logs}"
              attempt += 1

        if is_valid:
            self.redis_client.rpush('api_queue', json.dumps({
              "message": f"Marketing crew output passed rule validation: {rule_logs} Attempt: {attempt}",
              "type": "marketing"
            }))

        logging.info(f"completed processing marketing message")

    def process_queue(self, queue_name: str, processing_queue: str) -> Optional[str]:
        """
        Process messages from a queue using reliable queue pattern
        """
        # Blocking pop from queue
        task = self.redis_client.blpop(queue_name, timeout=0)
        
        if task:
            task = task[1]  # blpop returns a tuple (queue_name, task)
            try:
                message = json.loads(task)
                self.process_marketing_message(message)
            except json.JSONDecodeError:
                logging.warning("JSON decoding failed, passing message directly.")
                message = task  # Pass the message directly if JSON decoding fails
                
                self.process_marketing_message(message)
                
                logging.info(f"Successfully processed task from {queue_name}")
                return task
            
            except Exception as e:
                logging.error(f"Error processing message: worker {e}")
                import traceback
                logging.error(traceback.format_exc())
                # Message stays in processing queue for manual intervention
        
        return None

    def run(self):
        """
        Main worker loop
        """
        # logging.info("Worker started. Waiting for messages...")
        
        while True:
            try:
                # Process marketing queue
                self.process_queue('marketing_queue', 'marketing_processing')
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.1)
                
            except redis.RedisError as e:
                logging.error(f"Redis error: {e}")
                time.sleep(5)  # Wait before retrying
            except KeyboardInterrupt:
                logging.info("Worker stopped by user")
                break
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                time.sleep(5)  # Wait before retrying


def run():
    """
    Entry point function for the worker as defined in pyproject.toml
    """
    worker = QueueWorker()
    worker.run()


if __name__ == "__main__":
    run() 
