"""
Crew Manager Implementation

This module provides the CrewManager class which coordinates all infrastructure agents
and provides centralized services for Redis connection management, event distribution,
and agent lifecycle management.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, TypeVar, Generic, Type, Tuple
from dataclasses import dataclass
from enum import Enum

import redis
from redis.asyncio import Redis
from rdflib import Graph
from pydantic import BaseModel

from infrastructure_crew.agents.base_agent import BaseAgent
from infrastructure_crew.agents.registry_manager_agent import RegistryManagerAgent
from infrastructure_crew.agents.schema_validator_agent import SchemaValidatorAgent
from infrastructure_crew.agents.system_monitor_agent import SystemMonitorAgent # Keep SystemMonitorAgentConfig if it's from the schema import later

from infrastructure_crew.agents.cep_agent import CEPAgent
from infrastructure_crew.schemas.registry_manager_schema import RegistryManagerSchema
from infrastructure_crew.schemas.schema_validator_schema import SchemaValidatorSchema
from infrastructure_crew.schemas.system_monitor_schema import SystemMonitorSchema, SystemMonitorAgentConfig
from infrastructure_crew.schemas.knowledge_graph_ingestion_schema import KnowledgeGraphIngestionSchema, KnowledgeGraphIngestionAgentConfig
from infrastructure_crew.schemas.knowledge_graph_schema import KnowledgeGraphSchema, KnowledgeGraphQueryAgentConfig
from infrastructure_crew.schemas.llm_powered_knowledge_schema import LLMPoweredKnowledgeSchema, LLMPoweredKnowledgeAgentConfig
from infrastructure_crew.schemas.task_orchestration_schema import TaskOrchestrationSchema, TaskOrchestrationAgentConfig
from workers.example_worker_agent import ExampleWorkerAgent, ExampleWorkerAgentConfig
from common.models import AgentRegistration, ServiceRegistrationRequest, ServiceHeartbeat, EndpointType, ServiceStatus, ServiceEndpoint
from infrastructure.events import Event, EventPriority
from infrastructure_crew.schemas.event_schema import EventSchema, EventField, EventTypePriority, ServiceInfo  # For type hinting in validation passthrough

# Blockchain Integration
from infrastructure_crew.blockchain.consensus import ConsensusManager, ConsensusType
from infrastructure_crew.blockchain.transaction import TransactionManager
from infrastructure_crew.blockchain.smart_contract import SmartContractInterface

# Functional Crew Imports
from infrastructure_crew.translation_crew.translation_crew import TranslationCrew
from marketing_crew.marketing_crew import MarketingCrew
from inventory_crew.inventory_crew import InventoryCrew
# from infrastructure_crew.agents.state_agent import StateAgent # This might also need adjustment or removal if StateAgent is not found or used



# These imports might need to be adjusted if the modules are not available
# from infrastructure.memory.team import TeamMemory
# from infrastructure.memory.team_memory_manager import TeamMemoryManager

T = TypeVar('T')

class AgentState(Enum):
    """Enumeration of agent states."""
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"

class AgentHealth:
    """Represents the health status of an agent."""
    
    def __init__(self, agent_name: str, state: AgentState, 
                 last_heartbeat: float, error: Optional[str] = None):
        self.agent_name = agent_name
        self.state = state
        self.last_heartbeat = last_heartbeat
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert AgentHealth object to a dictionary."""
        return {
            "agent_name": self.agent_name,
            "state": self.state.value if isinstance(self.state, Enum) else self.state, # Ensure state is serializable
            "last_heartbeat": self.last_heartbeat,
            "error": self.error
        }

class Event:
    """Base class for all events."""
    
    def __init__(self, 
                 event_type: str, 
                 data: Dict[str, Any],
                 priority: EventPriority = EventPriority.MEDIUM):
        self.event_type = event_type
        self.data = data
        self.priority = priority
        self.timestamp = time.time()
        self.correlation_id = str(uuid.uuid4())

from .memory.memory_manager import MemoryManager
from .memory.team_memory_manager import TeamMemoryManager

class CrewManager:
    """
    Manages the infrastructure crew and provides centralized services.
    
    The CrewManager coordinates all infrastructure agents, manages Redis connections,
    handles event distribution, provides state synchronization services, and
    manages shared memory across teams.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the CrewManager.
        
        Args:
            config: Configuration dictionary for the manager
        """
        self.config = config
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_health: Dict[str, AgentHealth] = {}
        self.redis_pool: Optional[aioredis.Redis] = None
        self.event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.metrics: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        self._shutdown = False
        self.registry_manager_agent: Optional[RegistryManagerAgent] = None
        self.schema_validator_agent: Optional[SchemaValidatorAgent] = None
        self.system_monitor_agent: Optional[SystemMonitorAgent] = None
        self.knowledge_graph_ingestion_agent: Optional[KnowledgeGraphIngestionAgent] = None
        self.knowledge_graph_query_agent: Optional[KnowledgeGraphQueryAgent] = None
        self.llm_powered_knowledge_agent: Optional[LLMPoweredKnowledgeAgent] = None
        self.task_orchestration_agent: Optional[TaskOrchestrationAgent] = None
        self.example_worker_agent: Optional[ExampleWorkerAgent] = None
        self.rdf_graph: Optional[Graph] = None
        
        # Initialize blockchain components
        blockchain_config = config.get("blockchain_config", {})
        self.consensus_manager = ConsensusManager(
            consensus_type=ConsensusType[blockchain_config.get("consensus_type", "RAFT")],
            quorum_size=blockchain_config.get("quorum_size", 3),
            timeout_seconds=blockchain_config.get("timeout_seconds", 30.0)
        )
        self.transaction_manager = TransactionManager(
            required_confirmations=blockchain_config.get("required_confirmations", 3)
        )
        self.smart_contract_interface = SmartContractInterface()
        
        # Initialize memory management
        self.memory_manager = MemoryManager(config.get("memory_config", {}))
        self.team_memory_manager = TeamMemoryManager(config.get("team_memory_config", {}))
        
        # Initialize metrics
        self.metrics = {
            "event_count": 0,
            "error_count": 0,
            "processing_time": [],
            "agent_health": {},
            "redis_connections": 0,
            "memory_usage": self.memory_manager.get_memory_usage(),
            "team_memory_usage": self.team_memory_manager.get_system_memory_usage(),
            "services_registered_total": 0,
            "service_registrations_count": 0,
            "service_unregistrations_count": 0,
            "service_heartbeats_count": 0,
            "schema_validations_succeeded_count": 0,
            "schema_validations_failed_count": 0
        }
    
    async def initialize(self):
        """
        Initialize the crew manager and Redis connection.
        """
        self.rdf_graph = Graph() # Initialize the RDF graph
        try:
            # Initialize Redis connection
            self.redis_pool = Redis(
                connection_pool=redis.ConnectionPool.from_url(
                    self.config.get("redis_url", "redis://localhost:6379/0"),
                    max_connections=self.config.get("redis_max_connections", 10),
                    socket_timeout=self.config.get("redis_timeout", 5)
                )
            )
            
            # Initialize RegistryManagerAgent
            registry_agent_config = {
                "agent_id": self.config.get("registry_agent_id", "registry_manager_main"),
                "redis_url": self.config.get("redis_url", "redis://localhost:6379/0")
            }
            self.registry_manager_agent = RegistryManagerAgent(config=registry_agent_config, redis_client=self.redis_pool)
            
            if not await self.registry_manager_agent.initialize():
                self.logger.error("Failed to initialize RegistryManagerAgent. CrewManager initialization failed.")
                raise RuntimeError("Failed to initialize RegistryManagerAgent during CrewManager setup.")
            await self.registry_manager_agent.start()
            self.logger.info("RegistryManagerAgent initialized and started successfully.")

            # Initialize SchemaValidatorAgent
            validator_agent_config = {
                "agent_id": self.config.get("validator_agent_id", "schema_validator_main")
            }
            self.schema_validator_agent = SchemaValidatorAgent(config=validator_agent_config)
            if await self.schema_validator_agent.initialize():
                await self.schema_validator_agent.start()
                self.logger.info("SchemaValidatorAgent initialized and started successfully.")
            else:
                self.logger.error("Failed to initialize SchemaValidatorAgent. CrewManager initialization may be incomplete.")
                # Consider if this failure should halt CrewManager initialization

            # Initialize SystemMonitorAgent
            system_monitor_config_dict = self.config.get("system_monitor_agent_config", {})
            system_monitor_agent_id = system_monitor_config_dict.get("agent_id", "system_monitor_main")
            #     "redis_url": self.config.get("redis_url"), # Use .get for safety
            #     "namespace": "crew_manager"
            # }
            # Initialize KnowledgeGraphIngestionAgent
            kg_ingestion_agent_id_default = "kg_ingestion_main"
            kg_ingestion_config_dict = self.config.get("knowledge_graph_ingestion_agent_config", {})
            try:
                if "agent_id" not in kg_ingestion_config_dict:
                    kg_ingestion_config_dict["agent_id"] = kg_ingestion_agent_id_default
                
                kg_agent_pydantic_config = KnowledgeGraphIngestionAgentConfig(**kg_ingestion_config_dict)
                
                self.knowledge_graph_ingestion_agent = KnowledgeGraphIngestionAgent(
                    agent_id=kg_agent_pydantic_config.agent_id,
                    redis_pool=self.redis_pool,
                    config=kg_agent_pydantic_config,
                    rdf_graph=self.rdf_graph
                )
                if await self.knowledge_graph_ingestion_agent.initialize():
                    await self.knowledge_graph_ingestion_agent.start()
                    self.agents[self.knowledge_graph_ingestion_agent.agent_id] = self.knowledge_graph_ingestion_agent
                    self.logger.info(f"KnowledgeGraphIngestionAgent (ID: {self.knowledge_graph_ingestion_agent.agent_id}) initialized and started successfully.")
                else:
                    self.logger.error(f"Failed to initialize KnowledgeGraphIngestionAgent (ID: {kg_agent_pydantic_config.agent_id}).")
            except Exception as e:
                self.logger.error(f"Error during KnowledgeGraphIngestionAgent (ID: {kg_ingestion_config_dict.get('agent_id', kg_ingestion_agent_id_default)}) setup: {e}", exc_info=True)

            # Initialize KnowledgeGraphQueryAgent
            kg_query_agent_id_default = "kg_query_main"
            kg_query_config_dict = self.config.get("knowledge_graph_query_agent_config", {})
            try:
                if "agent_id" not in kg_query_config_dict:
                    kg_query_config_dict["agent_id"] = kg_query_agent_id_default
                
                kg_query_pydantic_config = KnowledgeGraphQueryAgentConfig(**kg_query_config_dict)
                self.knowledge_graph_query_agent = KnowledgeGraphQueryAgent(
                    agent_id=kg_query_pydantic_config.agent_id,
                    redis_pool=self.redis_pool, 
                    config=kg_query_pydantic_config,
                    rdf_graph=self.rdf_graph
                )
                if await self.knowledge_graph_query_agent.initialize():
                    await self.knowledge_graph_query_agent.start()
                    self.agents[self.knowledge_graph_query_agent.agent_id] = self.knowledge_graph_query_agent
                    self.logger.info(f"KnowledgeGraphQueryAgent (ID: {self.knowledge_graph_query_agent.agent_id}) initialized and started successfully.")
                else:
                    self.logger.error(f"Failed to initialize KnowledgeGraphQueryAgent (ID: {kg_query_pydantic_config.agent_id}).")
            except Exception as e:
                self.logger.error(f"Error during KnowledgeGraphQueryAgent (ID: {kg_query_config_dict.get('agent_id', kg_query_agent_id_default)}) setup: {e}", exc_info=True)

            # Initialize LLMPoweredKnowledgeAgent
            llm_knowledge_agent_id_default = "llm_knowledge_main"
            llm_knowledge_config_dict = self.config.get("llm_powered_knowledge_agent_config", {})
            try:
                if "agent_id" not in llm_knowledge_config_dict:
                    llm_knowledge_config_dict["agent_id"] = llm_knowledge_agent_id_default

                llm_knowledge_pydantic_config = LLMPoweredKnowledgeAgentConfig(**llm_knowledge_config_dict)
                
                if self.knowledge_graph_query_agent and self.knowledge_graph_query_agent.initialized:
                    self.llm_powered_knowledge_agent = LLMPoweredKnowledgeAgent(
                        agent_id=llm_knowledge_pydantic_config.agent_id,
                        kg_query_agent=self.knowledge_graph_query_agent,
                        config=llm_knowledge_pydantic_config
                    )
                    if await self.llm_powered_knowledge_agent.initialize():
                        await self.llm_powered_knowledge_agent.start()
                        self.agents[self.llm_powered_knowledge_agent.agent_id] = self.llm_powered_knowledge_agent
                        self.logger.info(f"LLMPoweredKnowledgeAgent (ID: {self.llm_powered_knowledge_agent.agent_id}) initialized and started successfully.")
                    else:
                        self.logger.error(f"Failed to initialize LLMPoweredKnowledgeAgent (ID: {llm_knowledge_pydantic_config.agent_id}).")
                else:
                    self.logger.error(f"Cannot initialize LLMPoweredKnowledgeAgent (ID: {llm_knowledge_config_dict.get('agent_id', llm_knowledge_agent_id_default)}) because KnowledgeGraphQueryAgent is not available or not initialized.")
            except Exception as e:
                self.logger.error(f"Error during LLMPoweredKnowledgeAgent (ID: {llm_knowledge_config_dict.get('agent_id', llm_knowledge_agent_id_default)}) setup: {e}", exc_info=True)

            # Initialize KnowledgeGraphQueryAgent
            kg_query_config_dict = self.config.get("knowledge_graph_query_agent_config", {})
            kg_query_agent_id_default = "kg_query_main"
            
            try:
                if "agent_id" not in kg_query_config_dict:
                    kg_query_config_dict["agent_id"] = kg_query_agent_id_default
                
                kg_query_pydantic_config = KnowledgeGraphQueryAgentConfig(**kg_query_config_dict)

                self.knowledge_graph_query_agent = KnowledgeGraphQueryAgent(
                    agent_id=kg_query_pydantic_config.agent_id,
                    config=kg_query_pydantic_config
                )
                if await self.knowledge_graph_query_agent.initialize():
                    await self.knowledge_graph_query_agent.start()
                    self.agents[self.knowledge_graph_query_agent.agent_id] = self.knowledge_graph_query_agent
                    self.logger.info(f"KnowledgeGraphQueryAgent (ID: {self.knowledge_graph_query_agent.agent_id}) initialized and started successfully.")
                else:
                    self.logger.error(f"Failed to initialize KnowledgeGraphQueryAgent (ID: {kg_query_pydantic_config.agent_id}).")
            except Exception as e:
                self.logger.error(f"Error during KnowledgeGraphQueryAgent (ID: {kg_query_config_dict.get('agent_id', kg_query_agent_id_default)}) setup: {e}", exc_info=True)

            # Initialize LLMPoweredKnowledgeAgent (depends on KnowledgeGraphQueryAgent)
            if self.knowledge_graph_query_agent and self.knowledge_graph_query_agent.initialized:
                llm_knowledge_config_dict = self.config.get("llm_powered_knowledge_agent_config", {})
                llm_knowledge_agent_id_default = "llm_knowledge_main" # Default if not in dict
                
                try:
                    # Ensure agent_id from dict is passed to Pydantic model, or use default
                    if "agent_id" not in llm_knowledge_config_dict:
                        llm_knowledge_config_dict["agent_id"] = llm_knowledge_agent_id_default
                    
                    llm_knowledge_pydantic_config = LLMPoweredKnowledgeAgentConfig(**llm_knowledge_config_dict)

                    self.llm_powered_knowledge_agent = LLMPoweredKnowledgeAgent(
                        agent_id=llm_knowledge_pydantic_config.agent_id,
                        knowledge_graph_query_agent=self.knowledge_graph_query_agent,
                        config=llm_knowledge_pydantic_config
                    )
                    if await self.llm_powered_knowledge_agent.initialize():
                        await self.llm_powered_knowledge_agent.start()
                        self.agents[self.llm_powered_knowledge_agent.agent_id] = self.llm_powered_knowledge_agent
                        self.logger.info(f"LLMPoweredKnowledgeAgent (ID: {self.llm_powered_knowledge_agent.agent_id}) initialized and started successfully.")
                    else:
                        self.logger.error(f"Failed to initialize LLMPoweredKnowledgeAgent (ID: {llm_knowledge_pydantic_config.agent_id}).")
                except Exception as e:
                    self.logger.error(f"Error during LLMPoweredKnowledgeAgent (ID: {llm_knowledge_config_dict.get('agent_id', llm_knowledge_agent_id_default)}) setup: {e}", exc_info=True)
            else:
                self.logger.warning("KnowledgeGraphQueryAgent not available, LLMPoweredKnowledgeAgent will not be initialized.")

            # Initialize TaskOrchestrationAgent
            task_orch_config_dict = self.config.get("task_orchestration_agent_config", {})
            task_orch_agent_id_default = "task_orchestrator_main"
            try:
                if "agent_id" not in task_orch_config_dict:
                    task_orch_config_dict["agent_id"] = task_orch_agent_id_default
                
                task_orch_pydantic_config = TaskOrchestrationAgentConfig(**task_orch_config_dict)
                self.task_orchestration_agent = TaskOrchestrationAgent(
                    agent_id=task_orch_pydantic_config.agent_id,
                    redis_pool=self.redis_pool, # Pass the redis_pool
                    config=task_orch_pydantic_config
                )
                if await self.task_orchestration_agent.initialize():
                    await self.task_orchestration_agent.start()
                    self.agents[self.task_orchestration_agent.agent_id] = self.task_orchestration_agent
                    self.logger.info(f"TaskOrchestrationAgent (ID: {self.task_orchestration_agent.agent_id}) initialized and started successfully.")
                else:
                    self.logger.error(f"Failed to initialize TaskOrchestrationAgent (ID: {task_orch_pydantic_config.agent_id}).")
            except Exception as e:
                self.logger.error(f"Error during TaskOrchestrationAgent (ID: {task_orch_config_dict.get('agent_id', task_orch_agent_id_default)}) setup: {e}", exc_info=True)

            # Initialize ExampleWorkerAgent
            example_worker_config = self.config.get("example_worker_agent_config")
            if example_worker_config:
                if self.redis_pool and self.task_orchestration_agent: # Ensure dependencies are met
                    try:
                        example_worker_pydantic_config = ExampleWorkerAgentConfig(**example_worker_config)
                        self.example_worker_agent = ExampleWorkerAgent(
                            agent_id=example_worker_pydantic_config.agent_id,
                            redis_pool=self.redis_pool,
                            task_orchestrator=self.task_orchestration_agent,
                            config=example_worker_pydantic_config
                        )
                        if await self.example_worker_agent.initialize():
                            self.add_agent(self.example_worker_agent)
                            self.logger.info("ExampleWorkerAgent initialized and added to crew.")
                        else:
                            self.logger.error("Failed to initialize ExampleWorkerAgent.")
                    except Exception as e:
                        self.logger.error(f"Error initializing ExampleWorkerAgent: {e}", exc_info=True)
                else:
                    self.logger.error("Cannot initialize ExampleWorkerAgent: Redis pool or TaskOrchestrationAgent not available.")
            else:
                self.logger.warning("ExampleWorkerAgent config not found. Skipping initialization.")
                # Consider if this failure should halt CrewManager initialization

            # Start health monitoring
            self._health_monitor_task = asyncio.create_task(self._health_monitor())
            
            # Initialize memory management
            await self.memory_manager.initialize()
            await self.team_memory_manager.initialize()
            
            self.logger.info("CrewManager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing CrewManager: {e}", exc_info=True)
            # Optionally, set a flag here to indicate failed initialization to prevent further operations
            # self.is_initialized = False 
            raise # Re-raise the exception to ensure the caller knows initialization failed

    # --- Service Registry Passthrough Methods ---
    async def register_service(self, registration_request: ServiceRegistrationRequest) -> Optional[ServiceInfo]:
        if not self.registry_manager_agent or not self.registry_manager_agent.initialized:
            self.logger.error("RegistryManagerAgent not available for register_service call.")
            return None
        service_info = await self.registry_manager_agent.register_service(registration_request)
        if service_info:
            self.metrics["service_registrations_count"] += 1
            # We'll update services_registered_total in _update_metrics or by querying registry agent
        return service_info

    async def unregister_service(self, service_id: str) -> bool:
        if not self.registry_manager_agent or not self.registry_manager_agent.initialized:
            self.logger.error("RegistryManagerAgent not available for unregister_service call.")
            return False
        success = await self.registry_manager_agent.unregister_service(service_id)
        if success:
            self.metrics["service_unregistrations_count"] += 1
        return success

    async def get_service_info(self, service_id: str) -> Optional[ServiceInfo]:
        if not self.registry_manager_agent or not self.registry_manager_agent.initialized:
            self.logger.error("RegistryManagerAgent not available for get_service_info call.")
            return None
        return await self.registry_manager_agent.get_service_info(service_id)

    async def find_services_by_crew(self, crew_id: str) -> List[ServiceInfo]:
        if not self.registry_manager_agent or not self.registry_manager_agent.initialized:
            self.logger.error("RegistryManagerAgent not available for find_services_by_crew call.")
            return []
        return await self.registry_manager_agent.find_services_by_crew(crew_id)

    async def find_services_by_capability(self, capability: str) -> List[ServiceInfo]:
        if not self.registry_manager_agent or not self.registry_manager_agent.initialized:
            self.logger.error("RegistryManagerAgent not available for find_services_by_capability call.")
            return []
        return await self.registry_manager_agent.find_services_by_capability(capability)

    async def handle_service_heartbeat(self, heartbeat: ServiceHeartbeat) -> bool:
        if not self.registry_manager_agent or not self.registry_manager_agent.initialized:
            self.logger.error("RegistryManagerAgent not available for handle_service_heartbeat call.")
            return False
        success = await self.registry_manager_agent.handle_heartbeat(heartbeat)
        if success:
            self.metrics["service_heartbeats_count"] += 1
        return success

    # --- Schema Validator Passthrough Methods ---
    def validate_data_against_schema(self, data: Dict[str, Any], schema_identifier: str, is_event_type: bool = False) -> Tuple[bool, Optional[BaseModel], Optional[str]]:
        """Validates data against a schema specified by its ID or event type."""
        if not self.schema_validator_agent or not self.schema_validator_agent.initialized:
            self.logger.error("SchemaValidatorAgent not available for validate_data_against_schema call.")
            return False, None, "SchemaValidatorAgent not available."
        is_valid, model, error = self.schema_validator_agent.validate_data(data, schema_identifier, is_event_type)
        if is_valid:
            self.metrics["schema_validations_succeeded_count"] += 1
        else:
            self.metrics["schema_validations_failed_count"] += 1
        return is_valid, model, error

    def get_event_schema(self, event_type: str) -> Optional[Type[BaseEvent]]:
        """Retrieves the Pydantic model for a given event type."""
        if not self.schema_validator_agent or not self.schema_validator_agent.initialized:
            self.logger.error("SchemaValidatorAgent not available for get_event_schema call.")
            return None
        return self.schema_validator_agent.get_schema_by_event_type(event_type)

    async def add_agent(self, agent: BaseAgent):
        """
        Add an agent to the crew.
        
        Args:
            agent: The agent to add
        """
        if agent.name in self.agents:
            raise ValueError(f"Agent with name {agent.name} already exists")
            
        self.agents[agent.name] = agent
        agent.redis_pool = self.redis_pool
        
        # Initialize agent health tracking
        self.agent_health[agent.name] = AgentHealth(
            agent_name=agent.name,
            state=AgentState.INITIALIZING,
            last_heartbeat=time.time()
        )
        
        try:
            await agent.initialize()
            self.agent_health[agent.name].state = AgentState.READY
            self.logger.info(f"Agent {agent.name} initialized successfully")
            
        except Exception as e:
            self.agent_health[agent.name].state = AgentState.ERROR
            self.agent_health[agent.name].error = str(e)
            self.logger.error(f"Error initializing agent {agent.name}: {e}", exc_info=True)
    
    async def distribute_event(self, event: Event):
        """
        Distribute an event to relevant agents.
        
        Args:
            event: The event to distribute
        """
        if self._shutdown:
            raise RuntimeError("CrewManager is shutting down")
            
        try:
            await self.event_queue.put(event)
            self.metrics["event_count"] += 1
            
            # Process events in background
            if not hasattr(self, '_event_processor_task'):
                self._event_processor_task = asyncio.create_task(self._process_events())
                
        except Exception as e:
            self.logger.error(f"Error distributing event: {e}", exc_info=True)
            self.metrics["error_count"] += 1
            raise
    
    async def _process_events(self):
        """
        Process events from the queue.
        
        This method runs continuously in the background and processes events
        based on their priority.
        """
        while not self._shutdown:
            try:
                event = await self.event_queue.get()
                start_time = time.time()
                
                # Route event to relevant agents
                for agent in self.agents.values():
                    if agent.can_handle_event(event):
                        try:
                            await agent.process_event(event)
                            self.metrics["processing_time"].append(time.time() - start_time)
                        except Exception as e:
                            self.logger.error(
                                f"Error processing event in {agent.name}: {e}",
                                exc_info=True
                            )
                            self.metrics["error_count"] += 1
                
                self.event_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in event processor: {e}", exc_info=True)
                self.metrics["error_count"] += 1
    
    async def _health_monitor(self):
        """
        Monitor agent health and system metrics.
        
        This method runs periodically to check agent health and update metrics.
        """
        while not self._shutdown:
            try:
                # Update agent health status
                for agent_name, health_obj in self.agent_health.items():
                    # Example: Check if agent is responsive based on a liveness timeout
                    # A more robust system would involve agents actively reporting heartbeats or status,
                    # which would update health_obj.last_heartbeat.
                    if health_obj.state == AgentState.READY and \
                       (time.time() - health_obj.last_heartbeat > self.config.get("agent_liveness_timeout", 120)):
                        self.logger.warning(f"Agent {agent_name} may be unresponsive (last heartbeat: {health_obj.last_heartbeat:.2f}). Marking as ERROR.")
                        health_obj.state = AgentState.ERROR
                        health_obj.error = "Agent unresponsive - liveness timeout"

                # Update metrics dictionary
                current_agent_health_metrics = {}
                for name, health_obj in self.agent_health.items():
                    current_agent_health_metrics[name] = health_obj.to_dict()
                self.metrics["agent_health"] = current_agent_health_metrics
                
                self.metrics["memory_usage"] = self.memory_manager.get_memory_usage()
                self.metrics["team_memory_usage"] = self.team_memory_manager.get_system_memory_usage()
                
                if self.redis_pool:
                    try:
                        await self.redis_pool.ping()
                        # Simplified metric for Redis connection status
                        self.metrics["redis_connections"] = 1 
                    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as redis_err:
                        self.logger.error(f"Redis connection lost during health monitor ping: {redis_err}")
                        self.metrics["redis_connections"] = 0
                else:
                    self.metrics["redis_connections"] = 0

                # Update total registered services count
                if self.registry_manager_agent and self.registry_manager_agent.initialized and self.redis_pool:
                    try:
                        service_key_pattern = f"{self.registry_manager_agent.service_key_prefix}*"
                        all_service_keys = await self.redis_pool.keys(service_key_pattern)
                        self.metrics["services_registered_total"] = len(all_service_keys)
                    except Exception as e:
                        self.logger.error(f"Error updating services_registered_total metric: {e}", exc_info=True)
                        self.metrics["services_registered_total"] = -1 
                else:
                    self.metrics["services_registered_total"] = -1 if not (self.registry_manager_agent and self.registry_manager_agent.initialized) else 0
                
                # Optional: Persist metrics using state_agent if available and configured
                # if hasattr(self, 'state_agent') and self.state_agent and hasattr(self.state_agent, 'set'):
                #     try:
                #         await self.state_agent.set("crew_manager_metrics", self.metrics, ttl=self.config.get("metrics_ttl", 300))
                #     except Exception as e:
                #         self.logger.warning(f"Could not persist metrics via state_agent: {e}")

                await asyncio.sleep(self.config.get("health_monitor_interval", 10))
                
            except asyncio.CancelledError:
                self.logger.info("_health_monitor task has been cancelled.")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in _health_monitor loop: {e}", exc_info=True)
                await asyncio.sleep(self.config.get("health_monitor_error_interval", 30))
    
    async def shutdown(self):
        """
        Shutdown the crew manager and all agents.
        """
        self._shutdown = True
        
        # Cancel background tasks
        if hasattr(self, '_event_processor_task'):
            self._event_processor_task.cancel()
        if hasattr(self, '_health_monitor_task'):
            self._health_monitor_task.cancel()
        
        # Shutdown agents
        for agent_name, agent_instance in self.agents.items(): # Corrected iteration
            try:
                # Assuming BaseAgent has a 'stop' method as per RegistryManagerAgent's BaseAgent
                if hasattr(agent_instance, 'stop'): 
                    await agent_instance.stop()
                elif hasattr(agent_instance, 'shutdown'): # Fallback to 'shutdown' if 'stop' isn't there
                    await agent_instance.shutdown()
                self.agent_health[agent_name].state = AgentState.SHUTDOWN
                self.logger.info(f"Agent {agent_name} shut down successfully")
            except Exception as e:
                self.logger.error(f"Error shutting down agent {agent_name}: {e}", exc_info=True)

        # Shutdown RegistryManagerAgent
        if self.registry_manager_agent and self.registry_manager_agent.initialized:
            try:
                await self.registry_manager_agent.stop()
                self.logger.info("RegistryManagerAgent stopped successfully.")
            except Exception as e:
                self.logger.error(f"Error stopping RegistryManagerAgent: {e}", exc_info=True)

        # Shutdown SchemaValidatorAgent
        if self.schema_validator_agent and self.schema_validator_agent.initialized:
            try:
                await self.schema_validator_agent.stop()
                self.logger.info("SchemaValidatorAgent stopped successfully.")
            except Exception as e:
                self.logger.error(f"Error stopping SchemaValidatorAgent: {e}", exc_info=True)

        # Shutdown SystemMonitorAgent
        if self.system_monitor_agent and self.system_monitor_agent.initialized:
            try:
                await self.system_monitor_agent.stop()
                self.logger.info("SystemMonitorAgent stopped successfully.")
            except Exception as e:
                self.logger.error(f"Error stopping SystemMonitorAgent: {e}", exc_info=True)

        # Shutdown KnowledgeGraphIngestionAgent
        if self.knowledge_graph_ingestion_agent and self.knowledge_graph_ingestion_agent.initialized:
            try:
                await self.knowledge_graph_ingestion_agent.stop()
                self.logger.info("KnowledgeGraphIngestionAgent stopped successfully.")
            except Exception as e:
                self.logger.error(f"Error stopping KnowledgeGraphIngestionAgent: {e}", exc_info=True)

        # Shutdown KnowledgeGraphQueryAgent
        if self.knowledge_graph_query_agent and self.knowledge_graph_query_agent.initialized:
            try:
                await self.knowledge_graph_query_agent.stop()
                self.logger.info("KnowledgeGraphQueryAgent stopped successfully.")
            except Exception as e:
                self.logger.error(f"Error stopping KnowledgeGraphQueryAgent: {e}", exc_info=True)

        # Shutdown LLMPoweredKnowledgeAgent
        if self.llm_powered_knowledge_agent and self.llm_powered_knowledge_agent.initialized:
            try:
                await self.llm_powered_knowledge_agent.stop()
                self.logger.info("LLMPoweredKnowledgeAgent stopped successfully.")
            except Exception as e:
                self.logger.error(f"Error stopping LLMPoweredKnowledgeAgent: {e}", exc_info=True)

        # Shutdown TaskOrchestrationAgent
        if self.task_orchestration_agent and self.task_orchestration_agent.initialized:
            try:
                await self.task_orchestration_agent.stop()
                self.logger.info("TaskOrchestrationAgent stopped successfully.")
            except Exception as e:
                self.logger.error(f"Error stopping TaskOrchestrationAgent: {e}", exc_info=True)

        # Shutdown ExampleWorkerAgent
        if self.example_worker_agent and self.example_worker_agent.initialized:
            try:
                await self.example_worker_agent.stop()
                self.logger.info("ExampleWorkerAgent stopped successfully.")
            except Exception as e:
                self.logger.error(f"Error stopping ExampleWorkerAgent: {e}", exc_info=True)
        
        # Close Redis connection
        if self.redis_pool:
            await self.redis_pool.close()
        
        # Shutdown memory management
        await self.memory_manager.shutdown()
        await self.team_memory_manager.shutdown()
        
        self.logger.info("CrewManager shutdown complete")
    
        return self.agent_health.copy()
    
    async def get_state(self, key: str) -> Optional[Any]:
        """
        Get a value from the state store.
        
        Args:
            key: The key to retrieve
            
        Returns:
            The value associated with the key, or None if not found
        """
        return await self.state_agent.get(key)
    
    async def set_state(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the state store.
        
        Args:
            key: The key to set
            value: The value to store
            ttl: Optional time-to-live in seconds
            
        Returns:
            True if the operation was successful
        """
        return await self.state_agent.set(key, value, ttl=ttl)
    
    async def get_snapshot(self) -> Dict[str, Any]:
        """
        Get a snapshot of the current system state.
        
        Returns:
            Dictionary containing system state snapshot
        """
        return {
            "metrics": self.get_metrics(),
            "agent_health": self.get_agent_health(),
            "state": await self.state_agent.keys()
        }

    async def get_knowledge_graph_ingestion_agent(self) -> Optional[KnowledgeGraphIngestionAgent]:
        """Returns the KnowledgeGraphIngestionAgent instance."""
        return self.knowledge_graph_ingestion_agent

    async def get_knowledge_graph_query_agent(self) -> Optional[KnowledgeGraphQueryAgent]:
        """Returns the KnowledgeGraphQueryAgent instance."""
        return self.knowledge_graph_query_agent

    async def get_llm_powered_knowledge_agent(self) -> Optional[LLMPoweredKnowledgeAgent]:
        """Returns the LLMPoweredKnowledgeAgent instance."""
        return self.llm_powered_knowledge_agent

    async def get_task_orchestration_agent(self) -> Optional[TaskOrchestrationAgent]:
        """Returns the TaskOrchestrationAgent instance."""
        return self.task_orchestration_agent

    async def get_example_worker_agent(self) -> Optional[ExampleWorkerAgent]:
        """Returns the ExampleWorkerAgent instance."""
        return self.example_worker_agent
