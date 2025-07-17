import json
import redis
import logging
import traceback
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_redis_client():
    """Get Redis client connection"""
    redis_url = os.getenv('REDIS_URL')
    if not redis_url:
        raise ValueError("REDIS_URL environment variable is not set")
        
    try:
        redis_client = redis.from_url(
            url=redis_url,
            decode_responses=True
        )
        return redis_client
    except redis.RedisError as e:
        logging.error(f"Failed to connect to Redis: {str(e)}\n{traceback.format_exc()}")
        raise

def safe_redis_operation(func):
    """Decorator for safe Redis operations with error handling"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except redis.RedisError as e:
            logging.error(f"Redis operation error: {str(e)}\n{traceback.format_exc()}")
            return None
    return wrapper

@safe_redis_operation
def push_to_queue(redis_client, queue_name, data):
    """Safely push message to Redis queue"""
    redis_client.rpush(queue_name, json.dumps(data))

@safe_redis_operation
def get_from_queue(redis_client, queue_name, timeout=0):
    """Safely get message from Redis queue"""
    return redis_client.blpop(queue_name, timeout=timeout)

def handle_worker_error(redis_client, error, worker_type, task_id=None, error_queue='error-queue'):
    """Common error handling for workers"""
    error_msg = f"Error in {worker_type}: {str(error)}"
    logging.error(f"{error_msg}\n{traceback.format_exc()}")
    
    error_data = {
        "error": error_msg,
        "type": f"{worker_type}-error",
        "task_id": task_id,
        "timestamp": datetime.now().isoformat()
    }
    push_to_queue(redis_client, error_queue, error_data) 