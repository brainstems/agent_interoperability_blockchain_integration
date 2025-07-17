import asyncio
import json
import logging
from rdflib import Graph, URIRef, Literal, BNode
from pydantic import Field # Added for KnowledgeGraphIngestionAgentConfig
from typing import Optional, Dict, Any, List, Union
from datetime import datetime

from redis.asyncio import Redis as AsyncRedis
from pydantic import ValidationError

from ...common.base_agent import BaseAgent, AgentConfig
from ..schemas.event_schemas import (
    BaseEvent, # To handle generic events
    DataChangeEvent, 
    ServiceRegistrationRequest, # Assuming this is an event or data we can process
    ServiceInfo # From registration
)
from ..rdf_constants import (
    RDF_NS, XSD, TYPE_PROJECT, TYPE_AGENT, TYPE_AGENT_CREW,
    ORIGINAL_ID, ENTITY_TYPE_PROP, CREATED_AT, UPDATED_AT, NAME, DESCRIPTION, STATUS,
    START_DATE, END_DATE, REPOSITORY_URL, CURRENT_MILESTONE, BUDGET, PROJECT_HAS_MANAGER, DATA,
    HAS_REPUTATION, USES_SHARED_MEMORY, HAS_COMMUNICATION_PROTOCOL, HAS_COMMON_GOAL,
    SKILLS_DESCRIPTION, IS_SELF_ORGANIZING, HAS_AUTONOMY_LEVEL, ENABLES_CONTINUOUS_LEARNING,
    EXHIBITS_ADAPTATION, HAS_RESILIENCE_MECHANISM, HAS_FAULT_TOLERANCE,
    HAS_TRANSPARENT_INCENTIVES, HAS_GOVERNANCE_MODEL, IS_INTEROPERABLE, INTEROPERABILITY_DESCRIPTION,
    IS_COMPOSABLE, COMPOSABILITY_DESCRIPTION, MEMBER_OF_CREW, HAS_SKILL_DIVERSITY, HAS_MEMBER
)
from ..schemas.knowledge_graph_schemas import (
    KGEntity,
    Project,
    Task,
    Product,
    MarketSignal,
    PerformanceMetric,
    Decision,
    Outcome,
    KGRelationship,
    AgentSchema, # New
    AgentCrewSchema # New
)
from ..rdf_constants import (
    PROJECT_NS, NAME, DESCRIPTION, STATUS, ORIGINAL_ID, DATA, ENTITY_TYPE_PROP,
    START_DATE, END_DATE, PRIORITY, # Added for completeness
    RDF_NS, RDFS_NS, XSD_NS, 
    TYPE_PROJECT, TYPE_TASK, TYPE_PRODUCT, TYPE_MARKET_SIGNAL,
    TYPE_PERFORMANCE_METRIC, TYPE_DECISION, TYPE_OUTCOME,
    HAS_TASK, PART_OF_PROJECT, DEPENDS_ON,
    # New constants for Agent/Crew
    TYPE_AGENT, TYPE_AGENT_CREW,
    HAS_REPUTATION, USES_SHARED_MEMORY, HAS_COMMUNICATION_PROTOCOL, HAS_COMMON_GOAL,
    HAS_SKILL_DIVERSITY, IS_SELF_ORGANIZING, HAS_AUTONOMY_LEVEL,
    ENABLES_CONTINUOUS_LEARNING, EXHIBITS_ADAPTATION, HAS_RESILIENCE_MECHANISM,
    HAS_FAULT_TOLERANCE, HAS_TRANSPARENT_INCENTIVES, HAS_GOVERNANCE_MODEL,
    IS_INTEROPERABLE, IS_COMPOSABLE,
    MEMBER_OF_CREW, HAS_MEMBER # New relationships
)

logger = logging.getLogger(__name__)

class KnowledgeGraphIngestionAgentConfig(AgentConfig):
    event_channels: List[str] = Field(default_factory=lambda: ["system:events:all", "service:registry:events"])
    # Add any specific configurations needed for ingestion logic
    # Add any specific configurations needed for ingestion logic

class KnowledgeGraphIngestionAgent(BaseAgent):
    def __init__(self, 
                 agent_id: str, 
                 redis_pool: AsyncRedis,
                 rdf_graph: Graph, # Added RDF graph
                 config: Optional[KnowledgeGraphIngestionAgentConfig] = None):
        super().__init__(agent_id, config or KnowledgeGraphIngestionAgentConfig())
        self.redis_pool = redis_pool
        self.rdf_graph = rdf_graph # Store RDF graph instance
        self.config: KnowledgeGraphIngestionAgentConfig = self.config # Type hint
        self._subscriber_task: Optional[asyncio.Task] = None
        self.initialized = False

    async def _initialize(self) -> None:
        if not self.redis_pool:
            logger.error(f"[{self.agent_id}] Redis pool not provided. Cannot initialize.")
            return
        logger.info(f"[{self.agent_id}] KnowledgeGraphIngestionAgent initializing with config: {self.config.dict()}")
        self.initialized = True
        logger.info(f"[{self.agent_id}] KnowledgeGraphIngestionAgent initialized.")

    async def _process(self, request: Any) -> Any:
        """Processes an incoming request. Placeholder implementation."""
        logger.info(f"[{self.agent_id}] _process called with request: {request}")
        # Depending on the design, this might dispatch to specific ingest methods
        # or handle a generic data type.
        # For now, let's assume it's not directly used by tests or primary flows.
        # Or, if there's a common ingestion pattern, implement it here.
        if isinstance(request, (Project, Task, Product, MarketSignal, PerformanceMetric, Decision, Outcome, AgentSchema, AgentCrewSchema)):
            # This is a simplistic dispatch, real implementation might be more complex
            # and involve checking request type or a command within the request.
            if isinstance(request, Project):
                await self._add_project_to_graph(request)
            elif isinstance(request, AgentSchema):
                await self.add_agent(request)
            elif isinstance(request, AgentCrewSchema):
                await self.add_agent_crew(request)
            # Add other KGEntity types here
            else:
                logger.warning(f"[{self.agent_id}] Unhandled KGEntity type in _process: {type(request)}")
                return None # Or raise NotImplementedError
            return f"Processed {type(request).__name__} with ID: {request.id}"
        elif isinstance(request, DataChangeEvent):
            await self.handle_event_message(json.dumps(request.model_dump())) # Needs actual message format
            return "Processed DataChangeEvent"
        
        logger.warning(f"[{self.agent_id}] _process received unhandled request type: {type(request)}")
        # Consider raising NotImplementedError if this path should not be hit
        return None

    def _entity_uri(self, entity_id: str, entity_type_name: str) -> URIRef:
        """Helper to create a unique URI for an entity."""
        return PROJECT_NS[f"{entity_type_name.lower().replace('_', '-')}/{entity_id}"]

    async def _add_project_to_graph(self, project: Project):
        project_uri = self._entity_uri(project.id, "Project")
        self.rdf_graph.add((project_uri, RDF_NS.type, TYPE_PROJECT))
        original_id_triple = (project_uri, ORIGINAL_ID, Literal(project.id))
        self.rdf_graph.add(original_id_triple)
        logger.debug(f"[{self.agent_id}] ADDING TRIPLE for Project ORIGINAL_ID: {original_id_triple}")

        # Add entity type property
        entity_type_triple = (project_uri, ENTITY_TYPE_PROP, Literal(project.__class__.__name__))
        self.rdf_graph.add(entity_type_triple)
        logger.debug(f"[{self.agent_id}] ADDING TRIPLE for Project ENTITY_TYPE_PROP: {entity_type_triple}")

        # Add timestamps if they exist
        if hasattr(project, 'created_at') and project.created_at:
            created_at_triple = (project_uri, CREATED_AT, Literal(project.created_at.isoformat(), datatype=XSD.dateTime))
            self.rdf_graph.add(created_at_triple)
            logger.debug(f"[{self.agent_id}] ADDING TRIPLE for Project CREATED_AT: {created_at_triple}")
        if hasattr(project, 'updated_at') and project.updated_at:
            updated_at_triple = (project_uri, UPDATED_AT, Literal(project.updated_at.isoformat(), datatype=XSD.dateTime))
            self.rdf_graph.add(updated_at_triple)
            logger.debug(f"[{self.agent_id}] ADDING TRIPLE for Project UPDATED_AT: {updated_at_triple}")

        if project.name:
            self.rdf_graph.add((project_uri, NAME, Literal(project.name)))
        if project.description:
            self.rdf_graph.add((project_uri, DESCRIPTION, Literal(project.description)))
        if project.status:
            self.rdf_graph.add((project_uri, STATUS, Literal(project.status)))
        if project.start_date:
            self.rdf_graph.add((project_uri, START_DATE, Literal(project.start_date.isoformat(), datatype=XSD.dateTime)))
        if project.end_date:
            self.rdf_graph.add((project_uri, END_DATE, Literal(project.end_date.isoformat(), datatype=XSD.dateTime)))
        if project.repository_url:
            self.rdf_graph.add((project_uri, REPOSITORY_URL, Literal(project.repository_url)))
        if project.current_milestone:
            self.rdf_graph.add((project_uri, CURRENT_MILESTONE, Literal(project.current_milestone)))
        if project.budget is not None:
            self.rdf_graph.add((project_uri, BUDGET, Literal(project.budget, datatype=XSD.float)))
        if project.project_manager_id:
            self.rdf_graph.add((project_uri, PROJECT_HAS_MANAGER, Literal(project.project_manager_id)))
        if project.metadata:
            try:
                # Attempt to store as JSON string if rdflib supports RDF.JSON, otherwise just string
                # For simplicity, storing as plain string for now.
                metadata_str = json.dumps(project.metadata)
                self.rdf_graph.add((project_uri, DATA, Literal(metadata_str)))
            except TypeError as e:
                logger.error(f"[{self.agent_id}] Could not serialize metadata for project {project.id}: {e}")
                self.rdf_graph.add((project_uri, DATA, Literal(str(project.metadata)))) # Fallback to str
        
        logger.info(f"[{self.agent_id}] Added/Updated Project {project.id} to RDF graph. URI: {project_uri}")
        # For debugging, you can print graph size or serialize a small part
        # logger.debug(f"[{self.agent_id}] Graph size: {len(self.rdf_graph)}")

    # Helper to add common and characteristic properties
    def _add_entity_properties(self, entity_uri: URIRef, entity_data: KGEntity, property_map: Dict[str, URIRef]):
        if entity_data.name:
            self.rdf_graph.add((entity_uri, NAME, Literal(entity_data.name)))
        if entity_data.description:
            self.rdf_graph.add((entity_uri, DESCRIPTION, Literal(entity_data.description)))
        
        # Add original ID and entity type from KGEntity base
        original_id_triple = (entity_uri, ORIGINAL_ID, Literal(entity_data.id))
        self.rdf_graph.add(original_id_triple)
        logger.debug(f"[{self.agent_id}] ADDING TRIPLE for {entity_data.entity_type} ORIGINAL_ID: {original_id_triple}")
        
        entity_type_triple = (entity_uri, ENTITY_TYPE_PROP, Literal(entity_data.entity_type))
        self.rdf_graph.add(entity_type_triple)
        logger.debug(f"[{self.agent_id}] ADDING TRIPLE for {entity_data.entity_type} ENTITY_TYPE_PROP: {entity_type_triple}")

        if entity_data.metadata:
            try:
                metadata_str = json.dumps(entity_data.metadata)
                self.rdf_graph.add((entity_uri, DATA, Literal(metadata_str)))
            except TypeError as e:
                logger.error(f"[{self.agent_id}] Could not serialize metadata for {entity_data.id}: {e}")
                self.rdf_graph.add((entity_uri, DATA, Literal(str(entity_data.metadata))))

        for field_name, rdf_property in property_map.items():
            value = getattr(entity_data, field_name, None)
            if value is not None:
                if isinstance(value, bool):
                    self.rdf_graph.add((entity_uri, rdf_property, Literal(value, datatype=XSD_NS.boolean)))
                elif isinstance(value, (int, float)):
                    xsd_type = XSD_NS.integer if isinstance(value, int) else XSD_NS.double
                    self.rdf_graph.add((entity_uri, rdf_property, Literal(value, datatype=xsd_type)))
                elif isinstance(value, datetime):
                     self.rdf_graph.add((entity_uri, rdf_property, Literal(value.isoformat(), datatype=XSD_NS.dateTime)))
                else: # Assumed to be string or convertible to string
                    self.rdf_graph.add((entity_uri, rdf_property, Literal(str(value))))

    async def add_agent(self, agent_data: AgentSchema):
        agent_uri = self._entity_uri(agent_data.id, "Agent")
        self.rdf_graph.add((agent_uri, RDF_NS.type, TYPE_AGENT))

        property_map = {
            "created_at": CREATED_AT,
            "updated_at": UPDATED_AT,
            "reputation": HAS_REPUTATION,
            "shared_memory_info": USES_SHARED_MEMORY,
            "communication_protocol_info": HAS_COMMUNICATION_PROTOCOL,
            "common_goal_info": HAS_COMMON_GOAL,
            "skills_description": HAS_SKILL_DIVERSITY,
            "is_self_organizing": IS_SELF_ORGANIZING,
            "autonomy_level_description": HAS_AUTONOMY_LEVEL,
            "continuous_learning_enabled": ENABLES_CONTINUOUS_LEARNING,
            "adaptation_capability_description": EXHIBITS_ADAPTATION,
            "resilience_mechanisms_description": HAS_RESILIENCE_MECHANISM,
            "fault_tolerance_description": HAS_FAULT_TOLERANCE,
            "transparent_incentives_info": HAS_TRANSPARENT_INCENTIVES,
            "governance_model_info": HAS_GOVERNANCE_MODEL,
            "is_interoperable": IS_INTEROPERABLE,
            "interoperability_description": INTEROPERABILITY_DESCRIPTION, 
            "is_composable": IS_COMPOSABLE,
            "composability_description": COMPOSABILITY_DESCRIPTION 
        }
        self._add_entity_properties(agent_uri, agent_data, property_map)

        for crew_id in agent_data.member_of_crews:
            crew_uri = self._entity_uri(crew_id, "AgentCrew") 
            self.rdf_graph.add((agent_uri, MEMBER_OF_CREW, crew_uri))
        
        logger.info(f"[{self.agent_id}] Added/Updated Agent {agent_data.id} to RDF graph. URI: {agent_uri}")

    async def add_agent_crew(self, crew_data: AgentCrewSchema):
        crew_uri = self._entity_uri(crew_data.id, "AgentCrew")
        self.rdf_graph.add((crew_uri, RDF_NS.type, TYPE_AGENT_CREW))

        if crew_data.common_goal: # common_goal is mandatory in AgentCrewSchema
            self.rdf_graph.add((crew_uri, HAS_COMMON_GOAL, Literal(crew_data.common_goal)))

        property_map = {
            "created_at": CREATED_AT,
            "updated_at": UPDATED_AT,
            "reputation": HAS_REPUTATION,
            "shared_memory_info": USES_SHARED_MEMORY,
            "communication_protocol_info": HAS_COMMUNICATION_PROTOCOL,
            "skill_diversity_description": HAS_SKILL_DIVERSITY,
            "is_self_organizing": IS_SELF_ORGANIZING,
            "autonomy_level_description": HAS_AUTONOMY_LEVEL,
            "continuous_learning_enabled": ENABLES_CONTINUOUS_LEARNING,
            "adaptation_capability_description": EXHIBITS_ADAPTATION,
            "resilience_mechanisms_description": HAS_RESILIENCE_MECHANISM,
            "fault_tolerance_description": HAS_FAULT_TOLERANCE,
            "transparent_incentives_info": HAS_TRANSPARENT_INCENTIVES,
            "governance_model_info": HAS_GOVERNANCE_MODEL,
            "is_interoperable": IS_INTEROPERABLE,
            "interoperability_description": INTEROPERABILITY_DESCRIPTION, 
            "is_composable": IS_COMPOSABLE,
            "composability_description": COMPOSABILITY_DESCRIPTION 
        }
        self._add_entity_properties(crew_uri, crew_data, property_map)

        for agent_id in crew_data.has_members:
            agent_uri = self._entity_uri(agent_id, "Agent") 
            self.rdf_graph.add((crew_uri, HAS_MEMBER, agent_uri))

        logger.info(f"[{self.agent_id}] Added/Updated AgentCrew {crew_data.id} to RDF graph. URI: {crew_uri}")


    async def start(self):
        if not self.initialized:
            logger.warning(f"[{self.agent_id}] Agent not initialized. Call initialize() first.")
            await self.initialize()
            if not self.initialized:
                 logger.error(f"[{self.agent_id}] Initialization failed. Cannot start subscriber task.")
                 return

        if self._subscriber_task is None or self._subscriber_task.done():
            self._subscriber_task = asyncio.create_task(self._redis_subscriber_loop())
            logger.info(f"[{self.agent_id}] Redis subscriber task started for KG ingestion.")
        else:
            logger.info(f"[{self.agent_id}] KG ingestion subscriber task already running.")

    async def _redis_subscriber_loop(self):
        pubsub = self.redis_pool.pubsub()
        await pubsub.subscribe(*self.config.event_channels)
        logger.info(f"[{self.agent_id}] Subscribed to Redis channels for KG: {self.config.event_channels}")

        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    channel = message['channel'].decode('utf-8')
                    data_str = message['data'].decode('utf-8')
                    logger.debug(f"[{self.agent_id}] Received message on {channel} for KG ingestion.")
                    await self._process_message_for_kg(channel, data_str)
                await asyncio.sleep(0.01) 
        except asyncio.CancelledError:
            logger.info(f"[{self.agent_id}] KG Redis subscriber loop cancelled.")
        except aioredis.RedisError as e:
            logger.error(f"[{self.agent_id}] Redis error in KG subscriber loop: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"[{self.agent_id}] Unexpected error in KG subscriber loop: {e}", exc_info=True)
        finally:
            logger.info(f"[{self.agent_id}] Unsubscribing from KG Redis channels.")
            await pubsub.unsubscribe(*self.config.event_channels)
            await pubsub.close()

    async def _process_message_for_kg(self, channel: str, data_str: str):
        try:
            data = json.loads(data_str)
            event_type = data.get("event_type") # Assuming events follow BaseEvent structure

            # Example: Handling a generic DataChangeEvent
            if event_type == DataChangeEvent.event_type:
                event = DataChangeEvent.parse_obj(data)
                # Simplistic: if data change is about a 'project', create/update Project entity
                if event.payload.entity_type == "project" and event.payload.entity_id:
                    project_data = event.payload.data
                    project = Project(
                        id=event.payload.entity_id,
                        name=project_data.get("name"),
                        description=project_data.get("description"),
                        status=project_data.get("status"),
                        # ... other fields from project_data
                        metadata={"source_event_id": event.correlation_id, "channel": channel}
                    )
                    await self._add_project_to_graph(project)
                    # logger.info(f"[{self.agent_id}] KG Ingestion: Processed Project: {project.json(indent=2)}")
            
            # Example: Handling ServiceRegistrationRequest (if it were an event)
            # This part is speculative as ServiceRegistrationRequest is a schema, not an event itself.
            # Let's assume an event `service.registered` with payload `ServiceInfo`
            elif event_type == "service.registered": # Hypothetical event
                service_info = ServiceInfo.parse_obj(data.get("payload"))
                # Create a 'Service' KGEntity (if we had one) or link to a Project/Product
                service_kg = KGEntity(
                    id=service_info.service_id,
                    entity_type="ServiceInstance", # Example KG entity type
                    name=service_info.service_name,
                    description=f"Service instance for crew {service_info.crew_id}",
                    metadata={
                        "capabilities": service_info.capabilities,
                        "endpoints": [ep.dict() for ep in service_info.endpoints],
                        "source_event_id": data.get("correlation_id"),
                        "channel": channel
                    }
                )
                logger.info(f"[{self.agent_id}] KG Ingestion: Would create/update ServiceInstance: {service_kg.json(indent=2)}")
                
                # Potentially link this service to a Project if crew_id maps to a project
                # project_link = KGRelationship(...) 
                # logger.info(f"[{self.agent_id}] KG Ingestion: Would create relationship: {project_link.json(indent=2)}")

            # Add more handlers for other event types relevant to KG
            # e.g., TaskCreated, DecisionMade, MarketSignalReceived events

            else:
                logger.debug(f"[{self.agent_id}] No specific KG ingestion logic for event_type: {event_type} on channel {channel}")

        except (ValidationError, json.JSONDecodeError) as e:
            logger.error(f"[{self.agent_id}] Error parsing message for KG: {e}. Channel: {channel}, Data: {data_str[:500]}")
        except Exception as e:
            logger.error(f"[{self.agent_id}] General error processing message for KG: {e}. Channel: {channel}", exc_info=True)

    async def stop(self):
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                logger.info(f"[{self.agent_id}] KG subscriber task successfully cancelled.")
            self._subscriber_task = None
        self.initialized = False
        logger.info(f"[{self.agent_id}] KnowledgeGraphIngestionAgent stopped.")

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "initialized": self.initialized,
            "subscriber_task_running": self._subscriber_task is not None and not self._subscriber_task.done(),
            "config": self.config.dict()
        }
