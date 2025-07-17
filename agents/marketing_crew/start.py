from marketing_crew import MarketingCrew
from simulation_crew import SimulationCrew
from state import MarketingSystemState
import redis
import json
import logging
from concurrent.futures import ThreadPoolExecutor
import os
from datetime import datetime
import time
import traceback
from swarms.promotional.manager import PromotionalSwarmManager
from swarms.inventory.manager import InventorySwarmManager
from swarms.product_agent.manager import ProductSwarmManager
import threading
from swarms.memory.company import CompanyMemoryAgent
from swarms.memory.agent import EntityState

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def publish_message(queue_name, message, redis_client):
    try:
        redis_client.rpush(queue_name, json.dumps(message))
        logging.info(f"Successfully pushed message to {queue_name}")
    except redis.RedisError as e:
        logging.error(f"Error pushing message to Redis queue: {e}")


def initialize_managers(redis_client):
    """Initialize all swarm managers in separate threads"""
    managers = {
        'promotional': PromotionalSwarmManager(swarm_name='promotional'),
        'inventory': InventorySwarmManager(swarm_name='inventory'),
        'product': ProductSwarmManager(swarm_name='product')
    }
    
    manager_threads = {}
    
    for name, manager in managers.items():
        thread = threading.Thread(
            target=manager.start,
            name=f"{name}_manager",
            daemon=True
        )
        thread.start()
        manager_threads[name] = thread
        logging.info(f"{name.capitalize()} Swarm Manager started in thread")
    
    return manager_threads


def process_marketing_request(redis_client, message, managers):
    """Process marketing request with state from state.py"""
    try:
        # Initialize system state
        state = MarketingSystemState()
        logging.info("System state initialized")

        if message.get('next'):
            logging.info("Next instruction received")
            current_metrics_channels = message.get('metrics')
        else:
            # Define current metrics with full structure matching simulator output
            current_metrics_channels = {
                # Channel metrics
                "amazon": {
                    "roas": 3.8,
                    "ctr": 0.012,
                    "impressions": 1200,
                    "clicks": 14,
                    "spend": 1100,
                    "sales": 120,
                    "conversion_rate": 0.12,
                    "acos": 0.18
                },
                "retail_store": {
                    "roas": 3.5,
                    "ctr": 0.011,
                    "impressions": 1150,
                    "clicks": 13,
                    "spend": 1080,
                    "sales": 110,
                    "conversion_rate": 0.11,
                    "acos": 0.19
                },
                "social_media": {
                    "roas": 3.2,
                    "ctr": 0.010,
                    "impressions": 1100,
                    "clicks": 12,
                    "spend": 1050,
                    "sales": 100,
                    "conversion_rate": 0.10,
                    "acos": 0.20
                },
                # Customer insights
                "customer_insights": {
                    "segments": [
                        {
                            "segment_name": "luxury",
                            "demographics": {
                                "age_distribution": {
                                    "18-24": 0.10,
                                    "25-34": 0.20,
                                    "35-44": 0.30,
                                    "45-54": 0.25,
                                    "55+": 0.15
                                },
                                "income_brackets": {
                                    "low": 0.1,
                                    "medium": 0.3,
                                    "high": 0.6
                                },
                                "geographic_distribution": {
                                    "urban": 0.6,
                                    "suburban": 0.3,
                                    "rural": 0.1
                                }
                            },
                            "behavior_metrics": {
                                "purchase_frequency": {
                                    "weekly": 0.3,
                                    "monthly": 0.4,
                                    "quarterly": 0.2,
                                    "annually": 0.1
                                },
                                "channel_preference": {
                                    "amazon": 0.5,
                                    "retail_store": 0.3,
                                    "social_media": 0.2
                                },
                                "basket_size": 4.2
                            },
                            "satisfaction_metrics": {
                                "nps": 82,
                                "satisfaction_score": 4.6,
                                "repeat_purchase_rate": 0.75
                            },
                            "lifetime_value": 8500.00
                        }
                        # Additional segments (premium, mainstream, budget) would follow same structure
                    ],
                    "age_demographics": {
                        "18-24": {
                            "population_share": 0.15,
                            "purchase_frequency": "monthly",
                            "channel_preference": {
                                "amazon": 0.75,
                                "retail_store": 0.15,
                                "social_media": 0.10
                            }
                        }
                        # Additional age ranges would follow same structure
                    }
                },
                # Channel insights
                "channel_insights": {
                    "channels": [
                        {
                            "channel_name": "amazon",
                            "performance_metrics": {
                                "revenue": 500000.00,
                                "growth_rate": 0.15,
                                "market_share": 0.25,
                                "conversion_rate": 0.08,
                                "customer_acquisition_cost": 100.00
                            }
                        }
                        # Additional channels would follow same structure
                    ]
                }
            }

        # Print the combined markdown-formatted output
        logging.info("Pattern recognition output: %s", state.all_outputs)

        # Send metrics to all swarm managers via pub/sub
        metrics_message = {
            'type': 'metrics_update',
            'timestamp': datetime.now().isoformat(),
            'metrics': current_metrics_channels,
            'source': 'marketing_system'
        }
        
        # Publish to shared channel - all subscribed managers will receive it
        logging.info(f"Publishing message to state-swarm channel: {metrics_message}")
        publish_result = redis_client.publish("state-swarm", json.dumps(metrics_message))
        logging.info(f"Message published to state-swarm. Number of clients received: {publish_result}")
        
        # Get expected swarms from managers initialization
        expected_swarms = set(managers.keys())
        received_consensus = set()
        consensus_results = []
        
        # Wait for consensus messages with timeout
        timeout = 300  # seconds
        start_time = time.time()
        
        while len(received_consensus) < len(expected_swarms):
            if time.time() - start_time > timeout:
                logging.warning(f"Timeout waiting for consensus from swarms. Received from: {received_consensus}")
                break
                
            # Check for new consensus messages
            message = redis_client.blpop('consensus-output', timeout=1)
            if message:
                try:
                    consensus_data = json.loads(message[1])
                    swarm_name = consensus_data.get('swarm_name')
                    
                    if swarm_name in expected_swarms and swarm_name not in received_consensus:
                        received_consensus.add(swarm_name)
                        consensus_results.append(consensus_data)
                        logging.info(f"Received consensus from {swarm_name} swarm")
                except json.JSONDecodeError as e:
                    logging.error(f"Error decoding consensus message: {e}")
                except Exception as e:
                    logging.error(f"Error processing consensus message: {e}")
        
        # Log results
        if len(received_consensus) == len(expected_swarms):
          
            logging.info("Received consensus from all swarms")
            
            # Combine all consensus results into one message
            combined_consensus = {
                "type": "consensus_response",
                "timestamp": datetime.now().isoformat(),
                "swarm_results": {}
            }
            
            for result in consensus_results:
                swarm_name = result['swarm_name']
                combined_consensus["swarm_results"][swarm_name] = result
                logging.info(f"Consensus from {swarm_name}: {result}")
            
            # Store in company memory
            company_memory = CompanyMemoryAgent(
                company_id="sarah_ai",
                storage_dir="memories/company"
            )
            
            # Create entities from swarm results
            entities = [
                EntityState(
                    entity_id=swarm_name,
                    entity_type="swarm",
                    attributes=result
                )
                for swarm_name, result in combined_consensus["swarm_results"].items()
            ]
            
            # Store the consensus as a company memory
            memory = company_memory.create_memory(
                memory_id=f"consensus_{int(time.time())}",
                input_data={
                    "original_message": message,
                    "metrics": current_metrics_channels,
                    "timestamp": datetime.now().isoformat()
                },
                outcome=combined_consensus,
                company_state={
                    "active_swarms": list(expected_swarms),
                    "responding_swarms": list(received_consensus),
                    "consensus_status": "complete",
                    "processing_time": time.time() - start_time
                },
                entities=entities,
                source_type="swarm_consensus"
            )
            
            if memory:
                logging.info(f"Stored company-level memory: {memory.memory_id}")
            else:
                logging.info("Consensus did not meet company memory threshold")
            
            # Send combined results to both api_queue and simulation_queue
            publish_message("api_queue", combined_consensus, redis_client)
            publish_message("simulation_queue", combined_consensus, redis_client)
            logging.info("Combined consensus results sent to api_queue and simulation_queue")
        else:
            missing_swarms = expected_swarms - received_consensus
            error_message = {
                "type": "consensus_error",
                "timestamp": datetime.now().isoformat(),
                "message": f"Missing consensus from swarms: {missing_swarms}",
                "received_from": list(received_consensus)
            }
            publish_message("api_queue", error_message, redis_client)
            
            # Create partial consensus results with available data
            partial_consensus = {
                "type": "partial_consensus_response",
                "timestamp": datetime.now().isoformat(),
                "swarm_results": {
                    swarm_name: result 
                    for result in consensus_results 
                    for swarm_name in [result['swarm_name']]
                },
                "missing_swarms": list(missing_swarms)
            }
            
            # Send partial results to simulation queue
            publish_message("simulation_queue", partial_consensus, redis_client)
            logging.warning(f"Sent partial consensus results to simulation_queue. Missing swarms: {missing_swarms}")

    except Exception as e:
        logging.error(f"Error in marketing process: {str(e)}\nTraceback:\n{traceback.format_exc()}")
        publish_message("api_queue", {
            "message": f"Error in marketing process: {str(e)}\nTraceback:\n{traceback.format_exc()}",
            "type": "error"
        }, redis_client)


def main():
    logging.info("Starting Sarah instruction worker...")
    
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    redis_client = redis.from_url(
        url=redis_url,
        decode_responses=True
    )

    try:
        # Initialize all swarm managers
        manager_threads = initialize_managers(redis_client)
        logging.info("All swarm managers initialized")

        while True:  # Keep checking for messages
            try:
                # Wait for instruction on sarah_instruction queue
                message = redis_client.blpop('sarah_instruction', timeout=0)
                if message:
                    data = json.loads(message[1])
                    logging.info("Received instruction from sarah_instruction queue")
                    # Process the marketing request using state from state.py
                    process_marketing_request(redis_client, data, manager_threads)
                    logging.info("Finished processing message, waiting for next instruction...")
                    
            except redis.RedisError as e:
                logging.error(f"Redis error: {e}")
                logging.info("Attempting to reconnect in 5 seconds...")
                time.sleep(5)
                redis_client = redis.from_url(redis_url, decode_responses=True)
                    
    except KeyboardInterrupt:
        logging.info("Shutting down Sarah instruction worker...")
    finally:
        redis_client.close()
        logging.info("Redis connection closed")


if __name__ == "__main__":
    main()

