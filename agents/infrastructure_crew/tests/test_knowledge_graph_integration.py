import unittest
import uuid
import asyncio
import logging
from datetime import datetime, timezone

from rdflib import Graph, Literal, URIRef, XSD

from agents.infrastructure_crew.infrastructure_agents.knowledge_graph_ingestion_agent import KnowledgeGraphIngestionAgent
from agents.infrastructure_crew.infrastructure_agents.knowledge_graph_query_agent import KnowledgeGraphQueryAgent
from agents.infrastructure_crew.schemas.knowledge_graph_schemas import (
    Project, AgentSchema, AgentCrewSchema, KGEntity
)
from agents.infrastructure_crew import rdf_constants as rdfc

# Helper to generate unique IDs for testing
def generate_id(prefix: str = "test_entity") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

class TestKnowledgeGraphIntegration(unittest.TestCase):

    def setUp(self):
        """Set up a fresh RDF graph and agents for each test."""
        # Configure logging to show DEBUG messages for our agents
        logging.basicConfig(level=logging.WARNING) # Set default for other loggers
        logging.getLogger("agents.infrastructure_crew.agents.knowledge_graph_ingestion_agent").setLevel(logging.DEBUG)
        logging.getLogger("agents.infrastructure_crew.agents.knowledge_graph_query_agent").setLevel(logging.DEBUG)
        
        self.rdf_graph = Graph()
        # Bind namespaces for easier reading of RDF serializations (optional, but good for debugging)
        self.rdf_graph.bind("rdf", rdfc.RDF_NS)
        self.rdf_graph.bind("rdfs", rdfc.RDFS_NS)
        self.rdf_graph.bind("xsd", rdfc.XSD_NS)
        self.rdf_graph.bind("proj", rdfc.PROJECT_NS)
        self.rdf_graph.bind("agent", rdfc.AGENT_NS)
        self.rdf_graph.bind("crew", rdfc.AGENT_CREW_NS)
        self.rdf_graph.bind("char", rdfc.CHARACTERISTIC_NS)
        self.rdf_graph.bind("rel", rdfc.RELATIONSHIP_NS)

        # Initialize agents with the shared graph
        # Note: For KnowledgeGraphIngestionAgent, we might not need a full agent_id or config for these unit tests
        # unless specific methods rely on them. We are testing its graph manipulation capabilities.
        self.ingestion_agent = KnowledgeGraphIngestionAgent(
            agent_id="test_ingestion_agent",
            rdf_graph=self.rdf_graph,
            redis_pool=None,  # Not needed for these specific graph tests
            config={}
        )
        # Ensure it's marked as initialized if its internal logic requires it for graph operations
        self.ingestion_agent.initialized = True 

        self.query_agent = KnowledgeGraphQueryAgent(
            agent_id="test_query_agent",
            rdf_graph=self.rdf_graph,
            config={}
        )
        self.query_agent.initialized = True

    def test_placeholder(self):
        """A placeholder test to ensure the setup works."""
        self.assertTrue(True)

    def test_ingest_and_query_single_agent(self):
        """Test Case 2.1: Ingest and Query a Single Agent with all characteristics."""
        loop = asyncio.get_event_loop()
        agent_id = generate_id("agent")
        current_time = datetime.now(timezone.utc)

        agent_data = AgentSchema(
            id=agent_id,
            name=f"Test Agent {agent_id}",
            description="An agent created for testing purposes.",
            created_at=current_time,
            updated_at=current_time,
            metadata={"source": "unit_test", "version": "1.0"},
            reputation=0.95,
            shared_memory_info="Uses Redis shared memory",
            communication_protocol_info="Uses AMQP for messages",
            common_goal_info="Achieve test success",
            skills_description="RDF manipulation, SPARQL querying",
            is_self_organizing=True,
            autonomy_level_description="High autonomy",
            continuous_learning_enabled=False,
            adaptation_capability_description="Adapts to new RDF schemas",
            resilience_mechanisms_description="Retry logic for SPARQL queries",
            fault_tolerance_description="Can handle temporary graph unavailability",
            transparent_incentives_info="Receives test points for success",
            governance_model_info="Test-driven governance",
            is_interoperable=True,
            interoperability_description="Interacts via RDFLib and Pydantic",
            is_composable=False,
            composability_description="Not designed for composition in this test",
            member_of_crews=[]
        )

        loop.run_until_complete(self.ingestion_agent.add_agent(agent_data))

        retrieved_agent_dict = loop.run_until_complete(self.query_agent.get_entity_by_id(agent_id))

        self.assertIsNotNone(retrieved_agent_dict, "Agent should be found in the graph")
        
        # Verify common KGEntity properties
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.ORIGINAL_ID).split('/')[-1]), agent_id)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.ENTITY_TYPE_PROP).split('/')[-1]), "Agent")
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.NAME).split('/')[-1]), agent_data.name)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.DESCRIPTION).split('/')[-1]), agent_data.description)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.CREATED_AT).split('/')[-1]).isoformat(), current_time.isoformat())
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.UPDATED_AT).split('/')[-1]).isoformat(), current_time.isoformat())

        # Verify Agent-specific characteristic properties
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.HAS_REPUTATION).split('/')[-1]), agent_data.reputation)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.USES_SHARED_MEMORY).split('/')[-1]), agent_data.shared_memory_info)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.HAS_COMMUNICATION_PROTOCOL).split('/')[-1]), agent_data.communication_protocol_info)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.HAS_COMMON_GOAL).split('/')[-1]), agent_data.common_goal_info)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.HAS_SKILL_DIVERSITY).split('/')[-1]), agent_data.skills_description)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.IS_SELF_ORGANIZING).split('/')[-1]), agent_data.is_self_organizing)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.HAS_AUTONOMY_LEVEL).split('/')[-1]), agent_data.autonomy_level_description)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.ENABLES_CONTINUOUS_LEARNING).split('/')[-1]), agent_data.continuous_learning_enabled)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.EXHIBITS_ADAPTATION).split('/')[-1]), agent_data.adaptation_capability_description)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.HAS_RESILIENCE_MECHANISM).split('/')[-1]), agent_data.resilience_mechanisms_description)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.HAS_FAULT_TOLERANCE).split('/')[-1]), agent_data.fault_tolerance_description)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.HAS_TRANSPARENT_INCENTIVES).split('/')[-1]), agent_data.transparent_incentives_info)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.HAS_GOVERNANCE_MODEL).split('/')[-1]), agent_data.governance_model_info)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.IS_INTEROPERABLE).split('/')[-1]), agent_data.is_interoperable)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.INTEROPERABILITY_DESCRIPTION).split('/')[-1]), agent_data.interoperability_description)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.IS_COMPOSABLE).split('/')[-1]), agent_data.is_composable)
        self.assertEqual(retrieved_agent_dict.get(str(rdfc.COMPOSABILITY_DESCRIPTION).split('/')[-1]), agent_data.composability_description)

        # Check that member_of_crews is not present if empty
        self.assertIsNone(retrieved_agent_dict.get(str(rdfc.MEMBER_OF_CREW).split('/')[-1]), "Should not have crew membership in this test")

    def test_ingest_and_query_single_project(self):
        """Test Case 1.1: Ingest and Query a Single Project."""
        loop = asyncio.get_event_loop()
        project_id = generate_id("project")
        current_time = datetime.now(timezone.utc)

        project_data = Project(
            id=project_id,
            name=f"Test Project {project_id}",
            description="A project for testing KG integration.",
            created_at=current_time,
            updated_at=current_time,
            status="In Progress",
            start_date=current_time,
            end_date=None,
            metadata={"client": "TestClient", "priority": "High"},
            repository_url="http://example.com/repo/testproject",
            current_milestone="Initial Setup",
            budget=10000.00,
            project_manager_id=generate_id("manager")
        )

        # Assuming a method like add_project exists or _add_project_to_graph is accessible/used by a public method
        # For now, let's assume ingest_entity can handle Project type or there's an add_project method.
        # If _add_project_to_graph is the only way, the test plan implies its usage.
        # We'll try a generic approach first if add_project isn't directly available.
        # Based on add_agent, it's likely there's an add_project method.
        # Let's assume self.ingestion_agent.add_project(project_data) exists.
        # If not, this test will guide us to implement it or use the correct method.
        loop.run_until_complete(self.ingestion_agent._process(project_data)) # Using generic ingest_entity

        retrieved_project_dict = loop.run_until_complete(self.query_agent.get_entity_by_id(project_id))

        self.assertIsNotNone(retrieved_project_dict, "Project should be found in the graph")
        
        # Verify common KGEntity properties
        self.assertEqual(retrieved_project_dict.get(str(rdfc.ORIGINAL_ID).split('/')[-1]), project_id)
        self.assertEqual(retrieved_project_dict.get(str(rdfc.ENTITY_TYPE_PROP).split('/')[-1]), "Project") # Assuming entity_type is set to 'Project'
        self.assertEqual(retrieved_project_dict.get(str(rdfc.NAME).split('/')[-1]), project_data.name)
        self.assertEqual(retrieved_project_dict.get(str(rdfc.DESCRIPTION).split('/')[-1]), project_data.description)
        self.assertEqual(retrieved_project_dict.get(str(rdfc.CREATED_AT).split('/')[-1]).isoformat(), current_time.isoformat())
        self.assertEqual(retrieved_project_dict.get(str(rdfc.UPDATED_AT).split('/')[-1]).isoformat(), current_time.isoformat())

        # Verify Project-specific properties
        self.assertEqual(retrieved_project_dict.get(str(rdfc.STATUS).split('/')[-1]), project_data.status)
        self.assertEqual(retrieved_project_dict.get(str(rdfc.START_DATE).split('/')[-1]).isoformat(), current_time.isoformat())
        self.assertIsNone(retrieved_project_dict.get(str(rdfc.END_DATE).split('/')[-1]), "End date should not be set yet")
        self.assertEqual(retrieved_project_dict.get(str(rdfc.REPOSITORY_URL).split('/')[-1]), project_data.repository_url)
        self.assertEqual(retrieved_project_dict.get(str(rdfc.CURRENT_MILESTONE).split('/')[-1]), project_data.current_milestone)
        self.assertEqual(float(retrieved_project_dict.get(str(rdfc.BUDGET).split('/')[-1])), project_data.budget)
        # Assuming PROJECT_MANAGER_ID is a relationship or a literal ID string
        # If it's a relationship, this check would be different (e.g., checking for a related entity)
        # For now, assuming it's stored as a literal string if not explicitly a relationship URI.
        # The schema for Project in knowledge_graph_schemas.py would define how project_manager_id is handled.
        # Let's assume it's stored as a literal for now, as per typical characteristic handling.
        self.assertEqual(retrieved_project_dict.get(str(rdfc.PROJECT_HAS_MANAGER).split('/')[-1]), project_data.project_manager_id)

    def test_ingest_and_query_single_agent_crew(self):
        """Test Case 2.2: Ingest and Query a Single AgentCrew with all characteristics."""
        loop = asyncio.get_event_loop()
        crew_id = generate_id("crew")
        current_time = datetime.now(timezone.utc)

        crew_data = AgentCrewSchema(
            id=crew_id,
            name=f"Test Crew {crew_id}",
            description="A crew created for testing purposes.",
            created_at=current_time,
            updated_at=current_time,
            metadata={"department": "testing_dept", "focus": "integration"},
            common_goal="Ensure robust KG agent and crew integration.",
            shared_memory_info="Utilizes a shared RDF graph for memory.",
            communication_protocol_info="Internal method calls and event bus.",
            skill_diversity_description="Diverse skills in RDF, SPARQL, and Python.",
            is_self_organizing=True,
            autonomy_level_description="Coordinates autonomously based on common goal.",
            continuous_learning_enabled=True,
            adaptation_capability_description="Adapts to new entity types and relationships.",
            resilience_mechanisms_description="Individual agent resilience contributes to crew resilience.",
            fault_tolerance_description="Can operate if some member agents are temporarily unavailable.",
            transparent_incentives_info="Shared success metrics for the crew.",
            governance_model_info="Lead agent coordinates, decisions by consensus.",
            is_interoperable=True,
            interoperability_description="Interacts with other systems via defined APIs.",
            is_composable=True,
            composability_description="Can be part of larger multi-crew systems.",
            has_members=[] # Will be tested in Test Case 2.3
        )

        # Assuming self.ingestion_agent.add_agent_crew(crew_data) or similar
        loop.run_until_complete(self.ingestion_agent._process(crew_data)) 

        retrieved_crew_dict = loop.run_until_complete(self.query_agent.get_entity_by_id(crew_id))

        self.assertIsNotNone(retrieved_crew_dict, "AgentCrew should be found in the graph")
        
        # Verify common KGEntity properties
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.ORIGINAL_ID).split('/')[-1]), crew_id)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.ENTITY_TYPE_PROP).split('/')[-1]), "AgentCrew")
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.NAME).split('/')[-1]), crew_data.name)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.DESCRIPTION).split('/')[-1]), crew_data.description)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.CREATED_AT).split('/')[-1]).isoformat(), current_time.isoformat())
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.UPDATED_AT).split('/')[-1]).isoformat(), current_time.isoformat())

        # Verify AgentCrew-specific characteristic properties (many are shared with Agent)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.HAS_COMMON_GOAL).split('/')[-1]), crew_data.common_goal)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.USES_SHARED_MEMORY).split('/')[-1]), crew_data.shared_memory_info)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.HAS_COMMUNICATION_PROTOCOL).split('/')[-1]), crew_data.communication_protocol_info)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.HAS_SKILL_DIVERSITY).split('/')[-1]), crew_data.skill_diversity_description)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.IS_SELF_ORGANIZING).split('/')[-1]), crew_data.is_self_organizing)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.HAS_AUTONOMY_LEVEL).split('/')[-1]), crew_data.autonomy_level_description)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.ENABLES_CONTINUOUS_LEARNING).split('/')[-1]), crew_data.continuous_learning_enabled)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.EXHIBITS_ADAPTATION).split('/')[-1]), crew_data.adaptation_capability_description)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.HAS_RESILIENCE_MECHANISM).split('/')[-1]), crew_data.resilience_mechanisms_description)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.HAS_FAULT_TOLERANCE).split('/')[-1]), crew_data.fault_tolerance_description)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.HAS_TRANSPARENT_INCENTIVES).split('/')[-1]), crew_data.transparent_incentives_info)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.HAS_GOVERNANCE_MODEL).split('/')[-1]), crew_data.governance_model_info)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.IS_INTEROPERABLE).split('/')[-1]), crew_data.is_interoperable)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.INTEROPERABILITY_DESCRIPTION).split('/')[-1]), crew_data.interoperability_description)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.IS_COMPOSABLE).split('/')[-1]), crew_data.is_composable)
        self.assertEqual(retrieved_crew_dict.get(str(rdfc.COMPOSABILITY_DESCRIPTION).split('/')[-1]), crew_data.composability_description)

        # Check that has_members is not present if empty
        self.assertIsNone(retrieved_crew_dict.get(str(rdfc.HAS_MEMBER).split('/')[-1]), "Should not have members in this test setup")

    def test_agent_crew_membership_relationships(self):
        """Test Case 2.3: Verify MEMBER_OF_CREW and HAS_MEMBER relationships."""
        loop = asyncio.get_event_loop()
        agent_id = generate_id("member_agent")
        crew_id = generate_id("member_crew")
        current_time = datetime.now(timezone.utc)

        agent_data = AgentSchema(
            id=agent_id,
            name=f"Agent {agent_id} for membership test",
            created_at=current_time,
            updated_at=current_time,
            member_of_crews=[crew_id] # Link to the crew
        )

        crew_data = AgentCrewSchema(
            id=crew_id,
            name=f"Crew {crew_id} for membership test",
            common_goal="Test membership relations",
            created_at=current_time,
            updated_at=current_time,
            has_members=[agent_id] # Link to the agent
        )

        # Ingest both agent and crew
        loop.run_until_complete(self.ingestion_agent._process(agent_data))
        loop.run_until_complete(self.ingestion_agent._process(crew_data))

        # Query for crews agent1 is a member of
        agent_crews_dicts = loop.run_until_complete(
            self.query_agent.get_related_entities(
                source_entity_id=agent_id, 
                relationship_type=rdfc.MEMBER_OF_CREW
            )
        )
        self.assertEqual(len(agent_crews_dicts), 1, "Agent should be a member of one crew")
        self.assertEqual(agent_crews_dicts[0].get(str(rdfc.ORIGINAL_ID).split('/')[-1]), crew_id, "Agent's crew ID should match")
        self.assertEqual(agent_crews_dicts[0].get(str(rdfc.NAME).split('/')[-1]), crew_data.name, "Agent's crew name should match")

        # Query for members of crew1
        crew_members_dicts = loop.run_until_complete(
            self.query_agent.get_related_entities(
                source_entity_id=crew_id, 
                relationship_type=rdfc.HAS_MEMBER
            )
        )
        self.assertEqual(len(crew_members_dicts), 1, "Crew should have one member")
        self.assertEqual(crew_members_dicts[0].get(str(rdfc.ORIGINAL_ID).split('/')[-1]), agent_id, "Crew's member ID should match")
        self.assertEqual(crew_members_dicts[0].get(str(rdfc.NAME).split('/')[-1]), agent_data.name, "Crew's member name should match")

    def test_find_entities_by_characteristics(self):
        """Test Case 2.4: Find Agents/Crews by Characteristics using find_entities."""
        loop = asyncio.get_event_loop()
        current_time = datetime.now(timezone.utc)

        # Ingest Agents with varying characteristics
        agent1_id = generate_id("find_agent1")
        agent1_data = AgentSchema(
            id=agent1_id, name="SelfOrganizing AgentRep0.8", created_at=current_time, updated_at=current_time,
            is_self_organizing=True, reputation=0.8
        )
        agent2_id = generate_id("find_agent2")
        agent2_data = AgentSchema(
            id=agent2_id, name="NonSelfOrganizing AgentRep0.5", created_at=current_time, updated_at=current_time,
            is_self_organizing=False, reputation=0.5
        )
        agent3_id = generate_id("find_agent3")
        agent3_data = AgentSchema(
            id=agent3_id, name="SelfOrganizing AgentRep0.5", created_at=current_time, updated_at=current_time,
            is_self_organizing=True, reputation=0.5
        )
        loop.run_until_complete(self.ingestion_agent._process(agent1_data))
        loop.run_until_complete(self.ingestion_agent._process(agent2_data))
        loop.run_until_complete(self.ingestion_agent._process(agent3_data))

        # Ingest AgentCrews with varying characteristics
        crew1_id = generate_id("find_crew1")
        crew1_data = AgentCrewSchema(
            id=crew1_id, name="Crew Goal Alpha", common_goal="Achieve Alpha", created_at=current_time, updated_at=current_time
        )
        crew2_id = generate_id("find_crew2")
        crew2_data = AgentCrewSchema(
            id=crew2_id, name="Crew Goal Beta", common_goal="Achieve Beta", created_at=current_time, updated_at=current_time
        )
        crew3_id = generate_id("find_crew3")
        crew3_data = AgentCrewSchema(
            id=crew3_id, name="Crew Specific Goal", common_goal="Specific Test Goal", created_at=current_time, updated_at=current_time
        )
        loop.run_until_complete(self.ingestion_agent._process(crew1_data))
        loop.run_until_complete(self.ingestion_agent._process(crew2_data))
        loop.run_until_complete(self.ingestion_agent._process(crew3_data))

        # Test: Find self-organizing agents
        self_organizing_agents = loop.run_until_complete(
            self.query_agent.find_entities(entity_type=rdfc.TYPE_AGENT.toPython(), properties={rdfc.IS_SELF_ORGANIZING: Literal(True)}) #Booleans are auto-typed by RDFLib to XSD.boolean
        )
        self.assertEqual(len(self_organizing_agents), 2)
        self_organizing_agent_ids = {agent.get(str(rdfc.ORIGINAL_ID).split('/')[-1]) for agent in self_organizing_agents}
        self.assertIn(agent1_id, self_organizing_agent_ids)
        self.assertIn(agent3_id, self_organizing_agent_ids)

        # Test: Find agents with reputation 0.8
        high_rep_agents = loop.run_until_complete(
            self.query_agent.find_entities(entity_type=rdfc.TYPE_AGENT.toPython(), properties={rdfc.HAS_REPUTATION: Literal(0.8, datatype=rdfc.XSD_NS.double)})
        )
        self.assertEqual(len(high_rep_agents), 1)
        self.assertEqual(high_rep_agents[0].get(str(rdfc.ORIGINAL_ID).split('/')[-1]), agent1_id)

        # Test: Find agents with reputation 0.5 (should be 2)
        medium_rep_agents = loop.run_until_complete(
            self.query_agent.find_entities(entity_type=rdfc.TYPE_AGENT.toPython(), properties={rdfc.HAS_REPUTATION: Literal(0.5, datatype=rdfc.XSD_NS.double)})
        )
        self.assertEqual(len(medium_rep_agents), 2)
        medium_rep_agent_ids = {agent.get(str(rdfc.ORIGINAL_ID).split('/')[-1]) for agent in medium_rep_agents}
        self.assertIn(agent2_id, medium_rep_agent_ids)
        self.assertIn(agent3_id, medium_rep_agent_ids)

        # Test: Find crews with common_goal "Specific Test Goal"
        specific_goal_crews = loop.run_until_complete(
            self.query_agent.find_entities(entity_type=rdfc.TYPE_AGENT_CREW.toPython(), properties={rdfc.HAS_COMMON_GOAL: Literal("Specific Test Goal")})
        )
        self.assertEqual(len(specific_goal_crews), 1)
        self.assertEqual(specific_goal_crews[0].get(str(rdfc.ORIGINAL_ID).split('/')[-1]), crew3_id)

    def test_handling_optional_fields_and_minimal_data(self):
        """Test Case 2.5: Ensure correct behavior with optional/None fields."""
        loop = asyncio.get_event_loop()
        current_time = datetime.now(timezone.utc) # For consistency if created_at/updated_at are checked

        # Test with minimal AgentSchema
        minimal_agent_id = generate_id("min_agent")
        # Per test plan: ID, entity_type. Name is practically useful for identification.
        # created_at, updated_at will be set by Pydantic default_factory if not provided.
        minimal_agent_data = AgentSchema(
            id=minimal_agent_id,
            name=f"Minimal Agent {minimal_agent_id}",
            # All other optional fields are omitted / default to None
            reputation=None, # Explicitly setting some to None for clarity
            skills_description=None
        )
        # Update created_at and updated_at to the fixed current_time for predictable assertions
        minimal_agent_data.created_at = current_time
        minimal_agent_data.updated_at = current_time

        loop.run_until_complete(self.ingestion_agent._process(minimal_agent_data))
        retrieved_minimal_agent = loop.run_until_complete(self.query_agent.get_entity_by_id(minimal_agent_id))

        self.assertIsNotNone(retrieved_minimal_agent, "Minimal agent should be found.")
        self.assertEqual(retrieved_minimal_agent.get(str(rdfc.ORIGINAL_ID).split('/')[-1]), minimal_agent_id)
        self.assertEqual(retrieved_minimal_agent.get(str(rdfc.ENTITY_TYPE_PROP).split('/')[-1]), "Agent")
        self.assertEqual(retrieved_minimal_agent.get(str(rdfc.NAME).split('/')[-1]), minimal_agent_data.name)
        self.assertEqual(retrieved_minimal_agent.get(str(rdfc.CREATED_AT).split('/')[-1]).isoformat(), current_time.isoformat())
        self.assertEqual(retrieved_minimal_agent.get(str(rdfc.UPDATED_AT).split('/')[-1]).isoformat(), current_time.isoformat())
        self.assertIsNone(retrieved_minimal_agent.get(str(rdfc.DESCRIPTION).split('/')[-1]))
        self.assertIsNone(retrieved_minimal_agent.get(str(rdfc.HAS_REPUTATION).split('/')[-1]))

        # Test querying a non-existent entity ID
        non_existent_id = "urn:uuid:this-id-does-not-exist"
        retrieved_non_existent = loop.run_until_complete(self.query_agent.get_entity_by_id(non_existent_id))
        self.assertIsNone(retrieved_non_existent)

        # Test find_entities with characteristics that don't match any entities
        no_match_entities = loop.run_until_complete(self.query_agent.find_entities(
            entity_type=rdfc.TYPE_AGENT.toPython(),
            properties={rdfc.NAME: Literal("This Name Does Not Exist In The Graph")} # find_entities expects full URI for property keys in query
        ))
        self.assertEqual(len(no_match_entities), 0)

        minimal_crew_id = generate_id("minimal_crew")
        minimal_crew_data = AgentCrewSchema(
            id=minimal_crew_id,
            name=f"Minimal Crew {minimal_crew_id}",
            common_goal="Achieve minimal testing."
            # All other optional fields are omitted / default to None
        )
        minimal_crew_data.created_at = current_time
        minimal_crew_data.updated_at = current_time

        loop.run_until_complete(self.ingestion_agent._process(minimal_crew_data))
        retrieved_minimal_crew = loop.run_until_complete(self.query_agent.get_entity_by_id(minimal_crew_id))

        self.assertIsNotNone(retrieved_minimal_crew, "Minimal crew should be found.")
        self.assertEqual(retrieved_minimal_crew.get(str(rdfc.ORIGINAL_ID).split('/')[-1]), minimal_crew_id)
        self.assertEqual(retrieved_minimal_crew.get(str(rdfc.NAME).split('/')[-1]), minimal_crew_data.name)
        self.assertEqual(retrieved_minimal_crew.get(str(rdfc.ENTITY_TYPE_PROP).split('/')[-1]), "AgentCrew")
        self.assertEqual(retrieved_minimal_crew.get(str(rdfc.HAS_COMMON_GOAL).split('/')[-1]), minimal_crew_data.common_goal)
        self.assertEqual(retrieved_minimal_crew.get(str(rdfc.CREATED_AT).split('/')[-1]).isoformat(), current_time.isoformat())
        self.assertEqual(retrieved_minimal_crew.get(str(rdfc.UPDATED_AT).split('/')[-1]).isoformat(), current_time.isoformat())

        # Check that optional fields set to None or omitted are not in the graph (or are None in dict)
        self.assertIsNone(retrieved_minimal_crew.get(str(rdfc.HAS_SKILL_DIVERSITY).split('/')[-1]), "Skill diversity should be None/absent.")
        self.assertIsNone(retrieved_minimal_crew.get(str(rdfc.IS_INTEROPERABLE).split('/')[-1]), "is_interoperable should be None/absent.")

    def test_execute_raw_sparql_query(self):
        """Test Case 3.1: Execute a raw SPARQL query."""
        loop = asyncio.get_event_loop()
        current_time = datetime.now(timezone.utc)
        sparql_agent_id = generate_id("sparql_agent")
        sparql_agent_name = f"Agent for SPARQL Test {sparql_agent_id}"

        agent_data = AgentSchema(
            id=sparql_agent_id,
            name=sparql_agent_name,
            created_at=current_time,
            updated_at=current_time,
            reputation=0.99
        )
        loop.run_until_complete(self.ingestion_agent._process(agent_data))

        # Custom SPARQL query to find the agent by its name and get its reputation
        query_string = f"""
        PREFIX kgagent: <{rdfc.AGENT_NS}>
        PREFIX rdf: <{rdfc.RDF_NS}>
        PREFIX rdfs: <{rdfc.RDFS_NS}>
        PREFIX xsd: <{rdfc.XSD_NS}>

        SELECT ?agent_id ?name ?reputation
        WHERE {{
            ?agent_uri rdf:type <{rdfc.TYPE_AGENT}> .
            ?agent_uri <{rdfc.ORIGINAL_ID}> ?agent_id .
            ?agent_uri <{rdfc.NAME}> ?name .
            ?agent_uri <{rdfc.HAS_REPUTATION}> ?reputation .
            FILTER(?agent_id = "{sparql_agent_id}")
            FILTER(?name = "{agent_data.name}")
        }}
    """

        results = loop.run_until_complete(self.query_agent.execute_raw_query(query_language="SPARQL", query_string=query_string))

        self.assertIsNotNone(results, "SPARQL query should return results.")
        self.assertEqual(len(results), 1, "SPARQL query should find exactly one agent.")

        result_row = results[0]
        # The keys in result_row will be the variable names from the SELECT clause
        self.assertEqual(str(result_row['agent_id']), sparql_agent_id)
        self.assertEqual(str(result_row['name']), sparql_agent_name)
        # RDFLib returns Literal for typed values, so compare its value
        self.assertAlmostEqual(float(result_row['reputation']), 0.99, places=2)

    def test_querying_non_existent_entities(self):
        """Test Case 3.2: Query for non-existent entities or relationships."""
        loop = asyncio.get_event_loop()
        non_existent_id = "urn:uuid:this-id-does-not-exist"

        # 1. Test get_entity_by_id for a non-existent ID
        retrieved_entity = loop.run_until_complete(self.query_agent.get_entity_by_id(non_existent_id))
        # Assuming get_entity_by_id returns None or an empty dict for non-existent entities
        # Based on current implementation, it returns an empty dict if not found after processing.
        # Let's check if it's falsy (empty dict or None)
        self.assertFalse(retrieved_entity, f"get_entity_by_id should return None or empty for {non_existent_id}")

        # 2. Test get_related_entities for a non-existent source ID
        related_entities = loop.run_until_complete(
            self.query_agent.get_related_entities(
                source_entity_id=non_existent_id, 
                relationship_type=rdfc.MEMBER_OF_CREW
            )
        )
        self.assertEqual(len(related_entities), 0, "get_related_entities should return empty list for non-existent source_id")

        # 3. Test find_entities with criteria that match no ingested entities
        # First, ingest a known entity to ensure the graph isn't completely empty, which might mask issues.
        agent_id = generate_id("existent_agent_for_nonexistent_query")
        agent_data = AgentSchema(id=agent_id, name="Existent Agent", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
        loop.run_until_complete(self.ingestion_agent._process(agent_data))

        # Now search for an entity with a highly unlikely characteristic
        non_matching_properties = {rdfc.NAME: Literal("This Name Does Not Exist In The Graph")}
        found_entities = loop.run_until_complete(
            self.query_agent.find_entities(entity_type=rdfc.TYPE_AGENT, properties=non_matching_properties)
        )
        self.assertEqual(len(found_entities), 0, "find_entities should return empty list for non-matching criteria")

        # Also test find_entities for a non-existent entity type (if your ontology is strict)
        # This might depend on how find_entities handles unknown types. Assuming it returns empty.
        non_existent_type_uri = URIRef("http://example.org/ontology/NonExistentType")
        found_entities_by_type = loop.run_until_complete(
            self.query_agent.find_entities(entity_type=non_existent_type_uri, properties={})
        )
        self.assertEqual(len(found_entities_by_type), 0, "find_entities should return empty list for non-existent entity type")


if __name__ == '__main__':
    unittest.main()
