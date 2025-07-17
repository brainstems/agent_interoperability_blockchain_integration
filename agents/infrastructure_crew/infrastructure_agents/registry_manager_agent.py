import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from redis.asyncio import Redis as AsyncRedis
from pydantic import ValidationError

from ..schemas.service_registry_schema import ServiceInfo, ServiceRegistrationRequest, ServiceHeartbeat, ServiceStatus
from ..schemas.learning_schemas import SharableLearning # Added for sharable learnings
from ..schemas.reputation_schemas import ReputationRating, AgentReputation # Added for reputation system
from .base_agent import InfrastructureBaseAgent

logger = logging.getLogger(__name__)

DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 60
DEFAULT_STALE_SERVICE_THRESHOLD_SECONDS = 180

class RegistryManagerAgent(InfrastructureBaseAgent):
    """Manages the lifecycle of service registrations, handles heartbeats, and prunes stale entries."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, redis_client: Optional[AsyncRedis] = None):
        super().__init__(config)
        self.agent_id = config.get("agent_id", "registry_manager_agent") if config else "registry_manager_agent"
        # Allow passing redis_client directly (e.g., for tests) or get from config
        if redis_client:
            self.redis: AsyncRedis = redis_client
        elif self.config.get("redis_url"):
            self.redis: AsyncRedis = AsyncRedis.from_url(self.config["redis_url"], decode_responses=False)
        else:
            raise ValueError("RegistryManagerAgent requires either a 'redis_client' instance or 'redis_url' in config.")
        self.service_key_prefix = "service_registry:service:"
        self.crew_services_key_prefix = "service_registry:crew_services:"
        self.capability_services_key_prefix = "service_registry:capability_services:"

        # Key prefixes for Sharable Learnings
        self.learning_object_key_prefix = "learnings:object:"
        self.learning_by_type_prefix = "learnings:by_type:"
        self.learning_by_source_prefix = "learnings:by_source:"
        self.learning_by_keyword_prefix = "learnings:by_keyword:"
        self.learning_all_ids_key = "learnings:all_ids"

        # Key prefixes for Reputation System
        self.reputation_profile_key_prefix = "reputation:profile:"
        self.reputation_ratings_list_key_prefix = "reputation:ratings_list:"

        self._heartbeat_check_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event() # Event for graceful shutdown of background tasks

    async def _get_service_key(self, service_id: str) -> str:
        return f"{self.service_key_prefix}{service_id}"

    async def _get_crew_services_key(self, crew_id: str) -> str:
        return f"{self.crew_services_key_prefix}{crew_id}"

    async def _get_capability_services_key(self, capability: str) -> str:
        return f"{self.capability_services_key_prefix}{capability}"

    # --- Helper methods for Sharable Learning keys ---
    def _get_learning_object_key(self, learning_id: str) -> str:
        return f"{self.learning_object_key_prefix}{learning_id}"

    def _get_learning_by_type_key(self, learning_type: str) -> str:
        return f"{self.learning_by_type_prefix}{learning_type.lower().replace(' ', '_')}"

    def _get_learning_by_source_key(self, source_entity_id: str) -> str:
        return f"{self.learning_by_source_prefix}{source_entity_id}"

    def _get_learning_by_keyword_key(self, keyword: str) -> str:
        return f"{self.learning_by_keyword_prefix}{keyword.lower().strip()}"

    # --- Helper methods for Reputation System keys ---
    def _get_reputation_profile_key(self, agent_id: str) -> str:
        return f"{self.reputation_profile_key_prefix}{agent_id}"

    def _get_reputation_ratings_list_key(self, agent_id: str) -> str:
        return f"{self.reputation_ratings_list_key_prefix}{agent_id}"

    async def register_service(self, registration_request: ServiceRegistrationRequest) -> Optional[ServiceInfo]:
        """Registers a new service."""
        try:
            service_info = ServiceInfo(**registration_request.model_dump(), registered_at=datetime.utcnow())
            service_info.last_heartbeat_at = datetime.utcnow() # Set initial heartbeat
            service_id = service_info.service_id
            service_key = await self._get_service_key(service_id)

            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.set(service_key, service_info.model_dump_json())
                pipe.sadd(await self._get_crew_services_key(service_info.crew_id), service_id)
                for capability in service_info.capabilities:
                    pipe.sadd(await self._get_capability_services_key(capability), service_id)
                await pipe.execute()
            
            logger.info(f"Service '{service_info.service_name}' (ID: {service_id}) registered by crew '{service_info.crew_id}'.")
            return service_info
        except ValidationError as e:
            logger.error(f"Validation error during service registration: {e}")
            return None
        except Exception as e:
            logger.error(f"Error registering service '{registration_request.service_name}': {e}", exc_info=True)
            return None

    async def unregister_service(self, service_id: str) -> bool:
        """Unregisters a service."""
        service_key = await self._get_service_key(service_id)
        service_data = await self.redis.get(service_key)
        if not service_data:
            logger.warning(f"Attempted to unregister non-existent service ID: {service_id}")
            return False
        
        try:
            service_info = ServiceInfo.model_validate_json(service_data)
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.delete(service_key)
                pipe.srem(await self._get_crew_services_key(service_info.crew_id), service_id)
                for capability in service_info.capabilities:
                    pipe.srem(await self._get_capability_services_key(capability), service_id)
                await pipe.execute()
            
            logger.info(f"Service '{service_info.service_name}' (ID: {service_id}) unregistered.")
            return True
        except Exception as e:
            logger.error(f"Error unregistering service ID '{service_id}': {e}", exc_info=True)
            return False

    async def get_service_info(self, service_id: str) -> Optional[ServiceInfo]:
        """Retrieves information for a specific service."""
        service_key = await self._get_service_key(service_id)
        service_data = await self.redis.get(service_key)
        if service_data:
            try:
                return ServiceInfo.model_validate_json(service_data)
            except ValidationError as e:
                logger.error(f"Data validation error for service ID '{service_id}': {e}")
                return None
        return None

    async def find_services_by_crew(self, crew_id: str) -> List[ServiceInfo]:
        """Finds all services registered by a specific crew."""
        service_ids = await self.redis.smembers(await self._get_crew_services_key(crew_id))
        services = []
        for service_id_bytes in service_ids:
            service_id = service_id_bytes.decode('utf-8')
            service_info = await self.get_service_info(service_id)
            if service_info:
                services.append(service_info)
        return services

    async def find_services_by_capability(self, capability: str) -> List[ServiceInfo]:
        """Finds all services that offer a specific capability."""
        service_ids = await self.redis.smembers(await self._get_capability_services_key(capability))
        services = []
        for service_id_bytes in service_ids:
            service_id = service_id_bytes.decode('utf-8')
            service_info = await self.get_service_info(service_id)
            if service_info:
                services.append(service_info)
        return services

    async def handle_heartbeat(self, heartbeat: ServiceHeartbeat) -> bool:
        """Handles a heartbeat from a service, updating its last_heartbeat_at time and status."""
        service_info = await self.get_service_info(heartbeat.service_id)
        if not service_info:
            logger.warning(f"Received heartbeat for unknown service ID: {heartbeat.service_id}")
            return False
        
        service_info.last_heartbeat_at = datetime.utcnow()
        if heartbeat.status:
            service_info.status = heartbeat.status
        
        try:
            await self.redis.set(await self._get_service_key(service_info.service_id), service_info.model_dump_json())
            logger.debug(f"Heartbeat received for service ID: {service_info.service_id}, Status: {service_info.status}")
            return True
        except Exception as e:
            logger.error(f"Error processing heartbeat for service ID '{service_info.service_id}': {e}", exc_info=True)
            return False

    async def _prune_stale_services(self):
        """Performs a single pass to check for and unregister services that haven't sent a heartbeat."""
        stale_threshold = datetime.utcnow() - timedelta(seconds=DEFAULT_STALE_SERVICE_THRESHOLD_SECONDS)
        # This is a simplified scan. For large number of services, consider SCAN with a cursor.
        all_service_keys_bytes = await self.redis.keys(f"{self.service_key_prefix}*")
        
        pruned_count = 0
        for service_key_bytes in all_service_keys_bytes:
            service_key = service_key_bytes.decode('utf-8')
            service_id = service_key.replace(self.service_key_prefix, "")
            service_info = await self.get_service_info(service_id)
            if service_info and service_info.last_heartbeat_at:
                if service_info.last_heartbeat_at < stale_threshold:
                    logger.warning(f"Service ID '{service_id}' is stale (last heartbeat: {service_info.last_heartbeat_at}). Unregistering.")
                    await self.unregister_service(service_id)
                    pruned_count += 1
            elif service_info and not service_info.last_heartbeat_at: # Should not happen if registered correctly
                 logger.warning(f"Service ID '{service_id}' has no last_heartbeat_at. Unregistering as potentially corrupt.")
                 await self.unregister_service(service_id)
                 pruned_count += 1
        
        if pruned_count > 0:
            logger.info(f"Pruned {pruned_count} stale services.")
        else:
            logger.debug("No stale services found during pruning check.")

    async def start_heartbeat_monitor(self, interval_seconds: int = DEFAULT_HEARTBEAT_INTERVAL_SECONDS):
        """Starts the background task to prune stale services."""
        if self._heartbeat_check_task and not self._heartbeat_check_task.done():
            logger.info("Heartbeat monitor already running.")
            return

        logger.info(f"Starting heartbeat monitor with check interval: {interval_seconds}s")
        # self._shutdown_event is already initialized in __init__

        async def _monitor_loop():
            logger.info("Heartbeat monitor loop started.")
            while not self._shutdown_event.is_set():
                try:
                    await self._prune_stale_services() # Call without arguments
                except Exception as e:
                    logger.error(f"Error in heartbeat monitor pruning cycle: {e}", exc_info=True)
                
                # Wait for the interval or until shutdown is signaled
                if self._shutdown_event.is_set(): # Check again before sleeping
                    break
                try:
                    # Wait for the timeout or the event to be set
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=interval_seconds)
                except asyncio.TimeoutError:
                    # This is expected, means the interval passed without shutdown
                    pass # Continue to the next iteration of the while loop
                except Exception as e:
                    logger.error(f"Error during heartbeat monitor sleep/wait: {e}", exc_info=True)
                    break # Exit loop on unexpected error during wait
            logger.info("Heartbeat monitor loop has exited.")

        self._heartbeat_check_task = asyncio.create_task(_monitor_loop())
        # In a real BaseAgent, you might have a more structured way to manage tasks

    # --- Methods for Sharable Learnings ---

    async def publish_learning(self, learning: SharableLearning) -> bool:
        """Publishes a sharable learning to the registry."""
        try:
            learning.touch() # Update the updated_at timestamp
            learning_key = self._get_learning_object_key(learning.learning_id)
            
            async with self.redis.pipeline(transaction=True) as pipe:
                # Store the learning object as JSON string
                pipe.set(learning_key, json.dumps(learning.to_redis_dict()))
                
                # Add to general set of all learning IDs
                pipe.sadd(self.learning_all_ids_key, learning.learning_id)
                
                # Add to type-specific set
                pipe.sadd(self._get_learning_by_type_key(learning.learning_type), learning.learning_id)
                
                # Add to source-specific set
                pipe.sadd(self._get_learning_by_source_key(learning.source_entity_id), learning.learning_id)
                
                # Add to keyword-specific sets
                for keyword in learning.keywords:
                    if keyword.strip(): # Ensure keyword is not empty
                        pipe.sadd(self._get_learning_by_keyword_key(keyword), learning.learning_id)
                
                await pipe.execute()
            
            logger.info(f"Learning '{learning.learning_id}' of type '{learning.learning_type}' from '{learning.source_entity_id}' published.")
            return True
        except ValidationError as e:
            logger.error(f"Validation error during learning publication for ID '{learning.learning_id}': {e}")
            return False
        except Exception as e:
            logger.error(f"Error publishing learning '{learning.learning_id}': {e}", exc_info=True)
            return False

    async def query_learnings(
        self,
        learning_type: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        source_entity_id: Optional[str] = None,
        limit: int = 100 # Default limit to prevent overwhelming results
    ) -> List[SharableLearning]:
        """Queries for sharable learnings based on criteria."""
        index_keys_to_intersect = []

        if learning_type:
            index_keys_to_intersect.append(self._get_learning_by_type_key(learning_type))
        if source_entity_id:
            index_keys_to_intersect.append(self._get_learning_by_source_key(source_entity_id))
        if keywords:
            for keyword in keywords:
                if keyword.strip():
                    index_keys_to_intersect.append(self._get_learning_by_keyword_key(keyword))

        learning_ids_bytes: List[bytes]
        if not index_keys_to_intersect:
            # No specific filters, get from all (respecting limit)
            # Using ZSCAN on a ZSET sorted by time might be better for 'all recent', but for now, SMEMBERS from all_ids
            learning_ids_bytes = await self.redis.srandmember(self.learning_all_ids_key, number=limit)
        elif len(index_keys_to_intersect) == 1:
            # Single index, use SMEMBERS (Redis doesn't have SINTER with one key)
            # SRANDMEMBER can also be used here if we want a random subset from a single large index
            learning_ids_bytes = await self.redis.smembers(index_keys_to_intersect[0]) 
        else:
            # Multiple indices, use SINTER
            learning_ids_bytes = await self.redis.sinter(index_keys_to_intersect)

        if not learning_ids_bytes:
            return []

        # Decode IDs and respect limit if SMEMBERS/SINTER returned more
        # Note: SINTER/SMEMBERS don't directly support limits in the command itself for count.
        # If `learning_ids_bytes` is very large, this in-memory slicing is okay, but for truly massive sets,
        # consider alternative strategies or Redis 7+ SINTERCARD with LIMIT (not available in older redis-py for SINTER).
        # For now, we fetch all intersected IDs and then limit.
        
        decoded_learning_ids = [lid.decode('utf-8') for lid in learning_ids_bytes][:limit]

        if not decoded_learning_ids:
            return []

        object_keys = [self._get_learning_object_key(lid) for lid in decoded_learning_ids]
        learning_data_list_bytes = await self.redis.mget(object_keys)

        learnings: List[SharableLearning] = []
        for i, data_bytes in enumerate(learning_data_list_bytes):
            if data_bytes:
                try:
                    # Assuming data_bytes is a JSON string from redis.set()
                    data_dict = json.loads(data_bytes.decode('utf-8'))
                    learnings.append(SharableLearning.from_redis_dict(data_dict))
                except (json.JSONDecodeError, ValidationError) as e:
                    logger.error(f"Error deserializing learning data for ID '{decoded_learning_ids[i]}': {e}")
            else:
                logger.warning(f"No data found for learning ID '{decoded_learning_ids[i]}' though it was indexed.")
        
        # Optionally sort by updated_at or created_at if needed, though this is client-side sorting.
        # learnings.sort(key=lambda x: x.updated_at, reverse=True)
        return learnings

    async def get_learning_by_id(self, learning_id: str) -> Optional[SharableLearning]:
        """Retrieves a specific learning by its ID."""
        learning_key = self._get_learning_object_key(learning_id)
        data_bytes = await self.redis.get(learning_key)
        if data_bytes:
            try:
                data_dict = json.loads(data_bytes.decode('utf-8'))
                return SharableLearning.from_redis_dict(data_dict)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.error(f"Error deserializing learning data for ID '{learning_id}': {e}")
        return None

    async def delete_learning(self, learning_id: str) -> bool:
        """Deletes a learning object and its indexes."""
        learning = await self.get_learning_by_id(learning_id)
        if not learning:
            logger.warning(f"Attempted to delete non-existent learning ID: {learning_id}")
            return False
        
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                # Remove from main object store
                pipe.delete(self._get_learning_object_key(learning_id))
                # Remove from 'all_ids' set
                pipe.srem(self.learning_all_ids_key, learning_id)
                # Remove from type index
                if learning.type: # Check if type exists before trying to use it as a key
                    pipe.srem(self._get_learning_by_type_key(learning.type), learning_id)
                # Remove from source index
                if learning.source_entity_id: # Check if source_entity_id exists
                    pipe.srem(self._get_learning_by_source_key(learning.source_entity_id), learning_id)
                # Remove from keyword indices
                for keyword in learning.keywords:
                    if keyword.strip(): # Ensure keyword is not empty or just whitespace
                        pipe.srem(self._get_learning_by_keyword_key(keyword), learning_id)
                await pipe.execute()
            logger.info(f"Learning '{learning_id}' deleted successfully.")
            return True
        except Exception as e:
            logger.error(f"Error deleting learning ID '{learning_id}': {e}", exc_info=True)
            return False

    # --- End of Methods for Sharable Learnings ---

    # --- Reputation System Methods ---

    async def record_rating(self, rating: ReputationRating) -> bool:
        """Records a reputation rating for an agent and updates their aggregate score."""
        if not isinstance(rating, ReputationRating):
            logger.error(f"Invalid rating object provided: {rating}")
            return False

        profile_key = self._get_reputation_profile_key(rating.rated_agent_id)
        ratings_list_key = self._get_reputation_ratings_list_key(rating.rated_agent_id)

        try:
            # Fetch current profile
            existing_profile_json = await self.redis.get(profile_key)
            
            if existing_profile_json:
                agent_rep = AgentReputation.model_validate_json(existing_profile_json)
            else:
                agent_rep = AgentReputation(agent_id=rating.rated_agent_id)
            
            # Update aggregate score
            if agent_rep.number_of_ratings == 0:
                agent_rep.average_score = rating.score
            else:
                # Numerically stable way to update average
                agent_rep.average_score = ((agent_rep.average_score * agent_rep.number_of_ratings) + rating.score) / (agent_rep.number_of_ratings + 1)
            agent_rep.number_of_ratings += 1
            agent_rep.last_updated = datetime.utcnow()

            async with self.redis.pipeline(transaction=True) as pipe:
                # Save the updated profile
                pipe.set(profile_key, agent_rep.model_dump_json())
                # Add new rating to the list of individual ratings
                pipe.lpush(ratings_list_key, rating.model_dump_json())
                # Limit the list of individual ratings to, say, the latest 100
                pipe.ltrim(ratings_list_key, 0, 99)
                await pipe.execute()
            
            logger.info(f"Recorded rating for agent '{rating.rated_agent_id}' by '{rating.rater_agent_id}'. New score: {agent_rep.average_score:.2f} ({agent_rep.number_of_ratings} ratings).")
            return True
        except ValidationError as e:
            logger.error(f"Validation error processing reputation for agent '{rating.rated_agent_id}': {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error recording rating for agent '{rating.rated_agent_id}': {e}", exc_info=True)
            return False

    async def get_agent_reputation(self, agent_id: str) -> Optional[AgentReputation]:
        """Retrieves the aggregated reputation for a specific agent."""
        profile_key = self._get_reputation_profile_key(agent_id)
        try:
            profile_json = await self.redis.get(profile_key)
            if profile_json:
                return AgentReputation.model_validate_json(profile_json)
            else:
                logger.debug(f"No reputation profile found for agent ID: {agent_id}")
                return None # Or return AgentReputation(agent_id=agent_id) for a default empty profile
        except ValidationError as e:
            logger.error(f"Data validation error for reputation profile of agent ID '{agent_id}': {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error retrieving reputation for agent ID '{agent_id}': {e}", exc_info=True)
            return None

    # --- End of Reputation System Methods ---

    async def stop_heartbeat_monitor(self):
        """Stops the background heartbeat monitor task."""
        if self._heartbeat_check_task and not self._heartbeat_check_task.done():
            logger.info("Stopping heartbeat monitor...")
            self._shutdown_event.set() # Assuming _shutdown_event is used to signal the task
            try:
                await asyncio.wait_for(self._heartbeat_check_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Heartbeat monitor task did not stop gracefully within timeout.")
                self._heartbeat_check_task.cancel()
            except Exception as e:
                 logger.error(f"Exception while stopping heartbeat monitor: {e}", exc_info=True)
        else:
            logger.info("Heartbeat monitor not running or already stopped.")

    async def initialize(self, **kwargs) -> bool:
        """Initialize the agent, including starting the heartbeat monitor."""
        await super().initialize(**kwargs) # Call parent initialize if it exists and does something
        self.logger.info(f"Initializing {self.agent_id}...")
        # Ensure Redis client is connected (some clients might require explicit connect)
        try:
            await self.redis.ping()
            self.logger.info("Successfully connected to Redis.")
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
            self.initialized = False
            return False
        
        await self.start_heartbeat_monitor()
        self.initialized = True
        self.logger.info(f"{self.agent_id} initialized successfully.")
        return True

    async def start(self):
        """Start the agent's operations. For RegistryManager, initialization is key."""
        if not self.initialized:
            self.logger.warning(f"{self.agent_id} cannot start, not initialized.")
            return
        await super().start() # Call parent start if it exists
        self.logger.info(f"{self.agent_id} started.")

    async def stop(self):
        """Stop the agent and clean up resources, including the heartbeat monitor."""
        self.logger.info(f"Stopping {self.agent_id}...")
        await self.stop_heartbeat_monitor()
        if hasattr(self.redis, 'close'): # Older redis-py versions might not have close for pool
             await self.redis.close() # Ensure Redis client connection is closed
        # await self.redis.connection_pool.disconnect() # For older versions or specific pool management
        await super().stop() # Call parent stop if it exists
        self.logger.info(f"{self.agent_id} stopped.")

    async def process_event(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        RegistryManagerAgent might not directly process general events via this method.
        It primarily offers its services (register, get_service, etc.) via direct method calls.
        However, it could listen for specific administrative commands if designed to.
        """
        self.logger.debug(f"{self.agent_id} received event: {event_data}. No direct processing implemented.")
        # Example: if event_data.get('command') == 'get_service_count':
        #     count = len(await self.redis.keys(f"{self.service_key_prefix}*"))
        #     return {'service_count': count}
        return None

# Example Usage (for testing, would be part of your main application setup)
async def example_main():
    # Ensure redis-py is installed with: pip install redis[hiredis]
    redis_client = AsyncRedis.from_url("redis://localhost:6379/0", decode_responses=False) # Important: decode_responses=False for direct JSON storage
    
    registry_agent = RegistryManagerAgent(redis_client=redis_client)
    await registry_agent.setup() # Start heartbeat monitor

    # Example service registration
    service_reg_req = ServiceRegistrationRequest(
        service_name="InventoryTranslator",
        crew_id="inventory_crew",
        capabilities=["translate_sales_to_inventory", "inventory_data_lookup"],
        endpoints=[
            {"type": "redis_pubsub", "address": "channel:inventory_translator_requests"},
            {"type": "http_api", "address": "http://inventory-service/translate"}
        ]
    )
    service_info = await registry_agent.register_service(service_reg_req)
    
    if service_info:
        print(f"Registered service: {service_info.model_dump_json(indent=2)}")

        # Example: Find service by capability
        found_services = await registry_agent.find_services_by_capability("translate_sales_to_inventory")
        print(f"Services with capability 'translate_sales_to_inventory': {len(found_services)}")
        if found_services:
            print(found_services[0].model_dump_json(indent=2))

        # Example: Heartbeat
        await asyncio.sleep(5)
        await registry_agent.handle_heartbeat(ServiceHeartbeat(service_id=service_info.service_id))
        retrieved_service = await registry_agent.get_service_info(service_info.service_id)
        if retrieved_service:
            print(f"Service after heartbeat: {retrieved_service.last_heartbeat_at}")

    # Simulate running for a bit to let heartbeat monitor work (or not, if interval is long)
    try:
        await asyncio.sleep(DEFAULT_HEARTBEAT_INTERVAL_SECONDS + 5) # Let it run one cycle
    except KeyboardInterrupt:
        pass
    finally:
        await registry_agent.cleanup() # Stop heartbeat monitor
        await redis_client.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Example of how RegistryManagerAgent might be instantiated and run
    async def example_run():
        agent_config = {
            "agent_id": "registry_manager_001",
            "redis_url": "redis://localhost:6379/0",
            # other BaseAgent configs
        }
        registry_agent = RegistryManagerAgent(config=agent_config)
        
        if await registry_agent.initialize():
            await registry_agent.start()
            
            # Example service registration
            service_reg_req = ServiceRegistrationRequest(
                service_name="InventoryTranslator",
                crew_id="inventory_crew",
                version="1.1",
                capabilities=["translate_sales_to_inventory", "inventory_data_lookup"],
                endpoints=[
                    {"type": EndpointType.REDIS_PUBSUB, "address": "channel:inventory_translator_requests"},
                    {"type": EndpointType.HTTP_API, "address": "http://inventory-service/translate"}
                ]
            )
            service_info = await registry_agent.register_service(service_reg_req)
            
            if service_info:
                registry_agent.logger.info(f"Registered service: {service_info.model_dump_json(indent=2)}")

                found_services = await registry_agent.find_services_by_capability("translate_sales_to_inventory")
                registry_agent.logger.info(f"Services with capability 'translate_sales_to_inventory': {len(found_services)}")
                if found_services:
                    registry_agent.logger.info(found_services[0].model_dump_json(indent=2))

                await asyncio.sleep(2) # Give some time for heartbeat or other ops
                await registry_agent.handle_heartbeat(ServiceHeartbeat(service_id=service_info.service_id))
                retrieved_service = await registry_agent.get_service_info(service_info.service_id)
                if retrieved_service:
                    registry_agent.logger.info(f"Service after heartbeat: {retrieved_service.last_heartbeat_at}")
            
            # Simulate running for a bit
            try:
                await asyncio.sleep(DEFAULT_HEARTBEAT_INTERVAL_SECONDS + 5) 
            except KeyboardInterrupt:
                registry_agent.logger.info("Keyboard interrupt received.")
            finally:
                await registry_agent.stop()
        else:
            registry_agent.logger.error("Failed to initialize RegistryManagerAgent.")

    asyncio.run(example_run())
