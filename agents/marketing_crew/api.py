from flask import Flask, request, jsonify
from flask_cors import CORS
import redis
import logging
from state import MarketingSystemState
import json

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Redis connection setup
redis_url = 'redis://default:z0wGFr1Q9X6TUjOMiMcL4AeG6a6G116Q@redis-18224.c10.us-east-1-4.ec2.redns.redis-cloud.com:18224'
redis_client = redis.from_url(
    url=redis_url,
    decode_responses=True
)

@app.route('/metrics/channels', methods=['GET'])
def get_channel_metrics():
    """Get current metrics for all advertising channels"""
    try:
        state = MarketingSystemState()
        metrics = state.get_current_metrics_channels()
        return jsonify({
            'status': 'success',
            'data': metrics
        }), 200
    except Exception as e:
        logging.error(f"Error getting channel metrics: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get channel metrics: {str(e)}'
        }), 500

@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        # Get the message from the request
        message = request.json.get('message')
        if not message:
            return jsonify({'error': 'No message provided'}), 400

        # Push the message to the Redis queue
        redis_client.rpush('sales_input_queue', message)
        return jsonify({'status': 'Message sent successfully'}), 200

    except redis.RedisError as e:
        return jsonify({'error': f'Redis error: {e}'}), 500

@app.route('/pop_message', methods=['GET'])
def pop_message():
    try:
        # Pop a message from the sales_input_queue
        message = redis_client.lpop('api_queue')
        if message:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'message': 'No messages in queue'}), 200

    except redis.RedisError as e:
        return jsonify({'error': f'Redis error: {e}'}), 500

@app.route('/state', methods=['GET'])
def get_state():
    try:
        state_manager = MarketingSystemState()
        return jsonify(state_manager.get_system_state())
    except Exception as e:
        return jsonify({
            'error': f'Error getting state: {str(e)}'
        }), 500

@app.route('/start_sarah', methods=['POST'])
def start_sarah():
    """Trigger Sarah's marketing process by sending a start message"""
    try:
        message = {'start': True}
        redis_client.rpush('sarah_instruction', json.dumps(message))
        return jsonify({
            'status': 'success',
            'message': 'Start instruction sent to Sarah'
        }), 200
    except redis.RedisError as e:
        logging.error(f"Redis error when starting Sarah: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to send start instruction: {str(e)}'
        }), 500

@app.route('/next_sarah', methods=['POST'])
def next_sarah():
    """Trigger Sarah's next marketing process by sending metrics data"""
    try:
        # Get metrics from request
        metrics = request.json.get('metrics')
        if not metrics:
            return jsonify({
                'status': 'error',
                'message': 'No metrics provided'
            }), 400

        message = {
            'next': True,
            'metrics': metrics
        }
        
        redis_client.rpush('sarah_instruction', json.dumps(message))
        return jsonify({
            'status': 'success',
            'message': 'Next instruction sent to Sarah'
        }), 200
    except redis.RedisError as e:
        logging.error(f"Redis error when sending next instruction to Sarah: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to send next instruction: {str(e)}'
        }), 500

if __name__ == "__main__":
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)  # Set log level to ERROR to suppress info logs
    app.run(host='0.0.0.0', port=5001) 