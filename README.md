# Agent Interoperability & Blockchain Integration

A cutting-edge multi-agent system leveraging CrewAI, Reinforcement Learning, and blockchain technology for distributed agent coordination and decentralized collaboration.

---

## [Section: Project Root README]

# Agent Interoperability & Blockchain Integration

## Overview

This project implements an advanced AI agent ecosystem that combines multi-agent systems with blockchain integration for secure, decentralized agent coordination. It features sophisticated agent organization, federated learning for collaborative model training, and specialized QA agents for performance analysis and continuous improvement.

## Agent Organization

The primary agent structure revolves around the `infrastructure_crew`, which serves as a central hub for various specialized agent functionalities.

### `infrastructure_crew`

Located at `agents/infrastructure_crew/`, this is the core crew responsible for foundational agent capabilities. It encompasses sub-crews and specialized agents that handle specific tasks.

Key sub-components and directories within `infrastructure_crew`:
*   **`agents/`**: This directory (`agents/infrastructure_crew/agents/`) houses the implementations of various specialized worker agents that perform specific tasks. Examples include `knowledge_graph_ingestion_agent.py`, `ambiguity_agent.py`, and `translation_qa_agent.py`.
*   **`qa_sub_crew/`**: (Formerly the top-level `qa_crew`) Located at `agents/infrastructure_crew/qa_sub_crew/`, this sub-crew is responsible for Quality Assurance tasks, primarily focused on evaluating project milestones. Its core agent, `QAAgent` (`agents/infrastructure_crew/qa_sub_crew/agents/qa_agent.py`), utilizes a federated learning system to improve its evaluation model.
*   **`translation_crew/`**: Located at `agents/infrastructure_crew/translation_crew/`, this sub-crew manages translation-related tasks. It likely orchestrates specialized translation agents (e.g., `inventory_translation_worker.py` found in `infrastructure_crew/agents/`).
*   **`tools/`**: Contains various tools used by the infrastructure agents, such as `FCEventSubscriberTool` and `FCPerformanceAnalyzerTool`.

### `TranslationQAAgent`

The `TranslationQAAgent` (defined in `agents/infrastructure_crew/agents/translation_qa_agent.py`) is a specialized QA agent. Its purpose is to:
*   Analyze the execution patterns and performance of the `TranslationCrew`.
*   Identify inefficiencies in the `TranslationCrew`'s planning, task decomposition, and internal information routing.
*   Utilize tools like `FCEventSubscriberTool` (to capture events from the `TranslationCrew`) and `FCPerformanceAnalyzerTool` (to analyze these events).
This agent provides meta-level QA by observing and reporting on the operational effectiveness of another agent crew.

## Service Registry and Discovery (`RegistryManagerAgent`)

The project includes a robust service registry and discovery mechanism, managed by the `RegistryManagerAgent` (located in `agents/infrastructure_crew/agents/registry_manager_agent.py`). This system allows agents and services to dynamically register their availability and capabilities, and for other components to discover and utilize them.

### Core Features:

1.  **Redis Backend**:
    *   The `RegistryManagerAgent` uses an asynchronous Redis client (`redis.asyncio.Redis`) as its persistent backend.
    *   Service information, crew-to-service mappings, and capability-to-service mappings are stored in Redis, ensuring scalability and data persistence.
    *   Specific key prefixes are used to organize data (e.g., `service_registry:service:<service_id>`).

2.  **Service Lifecycle Management**:
    *   **Registration (`register_service`)**:
        *   Services (e.g., other agents, tools) submit a `ServiceRegistrationRequest` (defined in `service_registry_schema.py`).
        *   The agent creates a `ServiceInfo` record, storing details like service ID, name, owning crew ID, offered capabilities, endpoint information, and registration/heartbeat timestamps.
        *   This `ServiceInfo` is stored in Redis. The service ID is also added to Redis sets associated with its `crew_id` and each of its `capabilities`.
    *   **Unregistration (`unregister_service`)**:
        *   Removes the service's primary record and its associations from the crew and capability sets in Redis.
    *   **Heartbeating (`handle_heartbeat`)**:
        *   Registered services are expected to periodically send `ServiceHeartbeat` messages.
        *   The `RegistryManagerAgent` updates the service's `last_heartbeat_at` timestamp and optionally its `status` (e.g., AVAILABLE, BUSY).
    *   **Stale Service Pruning (`_prune_stale_services`)**:
        *   A background monitoring task periodically checks for services that haven't sent a heartbeat within a configurable threshold (`DEFAULT_STALE_SERVICE_THRESHOLD_SECONDS`).
        *   Stale services are automatically unregistered to maintain an accurate registry of active services.

3.  **Service Discovery**:
    *   **By ID (`get_service_info`)**: Retrieve detailed information for a specific service if its ID is known.
    *   **By Crew (`find_services_by_crew`)**: Discover all services registered by a particular `crew_id`.
    *   **By Capability (`find_services_by_capability`)**: This is a key discovery method. Agents can query for services that offer a specific `capability` (e.g., "translation", "data_analysis"). The agent returns a list of all active services matching that capability.

4.  **Schema**:
    *   The system relies on Pydantic models defined in `agents/infrastructure_crew/schemas/service_registry_schema.py` for structuring service data (e.g., `ServiceInfo`, `ServiceRegistrationRequest`, `ServiceHeartbeat`, `ServiceStatus`).

### Usage:

The `CrewManager` (in `agents/infrastructure/crew_manager.py`) acts as a client to the `RegistryManagerAgent`, delegating service registration and unregistration requests, likely for services or agents spawned or managed by crews. Other agents within the system can then query the `RegistryManagerAgent` to find and interact with these registered services based on their needs.


## Contract Net Protocol and Task Marketplace

To facilitate dynamic task allocation and create a more adaptive multi-agent system, this project implements the Contract Net Protocol (CNP). This protocol allows agents to announce tasks, collect bids from capable worker agents, and award tasks based on bid evaluations, effectively creating a decentralized marketplace for tasks and services.

### 1. Contract Net Protocol (CNP) Implementation

The Contract Net Protocol provides a structured interaction pattern for task distribution and execution.

**Purpose:**
*   **Efficient Task Distribution**: Dynamically assign tasks to the most suitable available agents.
*   **Leveraging Specialization**: Enable agents with specific capabilities to bid for tasks they are well-suited to perform.
*   **Dynamic Resource Allocation**: Adapt to changing workloads and agent availability.

**Core Components & Flow:**

1.  **Task Initiator (`TaskOrchestrationAgent`):**
    *   Located in `agents/infrastructure_crew/agents/task_orchestration_agent.py`.
    *   Responsible for initiating tasks by broadcasting a **Call for Proposals (CFP)**.
    *   The CFP, defined by the `TaskAnnouncement` schema (see `agents/infrastructure_crew/schemas/contract_net_schemas.py`), details the task requirements, constraints, deadlines, and potentially the reward.
    *   Publishes CFPs to a designated Redis channel (e.g., `contract_net:cfp`).

2.  **Worker Agents (e.g., `BasicWorkerAgent`):**
    *   Specialized agents capable of performing tasks (e.g., `agents/infrastructure_crew/agents/basic_worker_agent.py`).
    *   Monitor the CFP channel for relevant task announcements.
    *   If a worker deems itself capable and willing to perform a task, it submits a **Bid**.
    *   Bids, defined by the `Bid` schema, include the worker's ID, the task ID, and any bid-specific information (e.g., proposed cost, estimated time, specific approach).
    *   Bids are sent to a Redis channel associated with the specific task or initiator (e.g., `contract_net:bids:<task_id>`).

3.  **Bid Evaluation and Task Awarding (by `TaskOrchestrationAgent`):**
    *   The `TaskOrchestrationAgent` collects bids for a defined period.
    *   It evaluates received bids based on criteria such as price, capability, estimated completion time, or other metrics.
    *   The task is awarded to the winning bidder. A `TaskAward` message is sent to the chosen worker.
    *   The winning worker acknowledges with a `TaskAcceptance` message. Other bidders may be notified that they were not selected.

4.  **Task Execution and Result Submission:**
    *   The awarded `WorkerAgent` executes the task.
    *   Upon completion, it submits the `TaskResult` (defined by the `TaskResult` schema) to the `TaskOrchestrationAgent`, typically via a dedicated Redis channel.

5.  **Confirmation and Completion:**
    *   The `TaskOrchestrationAgent` receives and processes the `TaskResult`.
    *   It may perform validation and then formally closes the task.
    *   (Future Scope: Integration with a payment or reputation system based on successful task completion).

**Communication Backbone:**
*   Redis streams or pub/sub channels are extensively used for:
    *   Broadcasting CFPs.
    *   Submitting bids.
    *   Sending task awards and acceptances.
    *   Delivering task results.

**Schemas:**
*   All data structures for the CNP interactions (e.g., `TaskAnnouncement`, `Bid`, `TaskAward`, `TaskResult`) are defined using Pydantic models in `agents/infrastructure_crew/schemas/contract_net_schemas.py`.

### 2. Agent Marketplace Functionality

The implementation of the Contract Net Protocol naturally gives rise to an agent marketplace.

**Concept:**
*   An environment where agents (task initiators) can "advertise" tasks needing completion, and other agents (workers) can "offer" their services by bidding on these tasks.
*   This fosters a competitive and efficient allocation of resources based on supply and demand for agent capabilities.

**Interaction with CNP:**
*   The CNP provides the fundamental mechanism for this marketplace: CFPs are the "demand," and bids represent the "supply."

**Synergy with Service Registry:**
*   The `RegistryManagerAgent` can play a crucial role:
    *   Worker agents can register their capabilities (e.g., "translation," "data_analysis," "code_generation") with the `RegistryManagerAgent`.
    *   `TaskOrchestrationAgents` could potentially query the registry to identify potentially capable agents and target CFPs more effectively or use this information during bid evaluation.
    *   Worker agents could use the registry to discover `TaskOrchestrationAgents` or filter CFPs based on their registered capabilities.

**Recent Developments & Testing:**
*   The `TaskOrchestrationAgent` has been enhanced with `_initialize` and `_process` methods to support its role in the CNP.
*   The `BasicWorkerAgent` serves as an initial example of a bidding agent.
*   The entire flow is intended to be tested using scripts like `run_contract_net_test.py` to simulate task announcements, bidding, awarding, and execution.

**Future Enhancements:**
*   More sophisticated bidding strategies for worker agents.
*   Advanced evaluation criteria for task initiators.
*   Integration of reputation systems for agents based on their performance in the marketplace.
*   Mechanisms for negotiation between initiators and bidders.

---

## [Section: agents/README.md]

# Infrastructure Agents with CrewAI Integration

This project provides a set of infrastructure agents that can be used with the [CrewAI](https://github.com/joaomdmoura/crewai) framework.

## Features

- **Modular Agent Architecture**: Easily extensible agent system
- **CrewAI Integration**: Seamless integration with the CrewAI framework
- **Pre-built Agents**: Common agent types for infrastructure tasks
- **Tool Integration**: Support for custom and built-in tools
- **Asynchronous Processing**: Built with asyncio for high performance

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/agent-blockchain-integration.git
   cd agent-blockchain-integration/agents
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install development dependencies (for testing and development):
   ```bash
   pip install -r requirements-dev.txt
   ```

## Quick Start

```python
import asyncio
from infrastructure.agents import DecisionAgent, RulesAgent
from infrastructure.crewai import CrewAIAgentAdapter, InfrastructureTask
from crewai import Crew, Process

async def main():
    # Create your infrastructure agents
    decision_agent = DecisionAgent()
    rules_agent = RulesAgent()

    # Create tasks
    decision_task = InfrastructureTask(
        agent=decision_agent,
        description="Make decisions based on input data",
        expected_output="A list of decisions with confidence scores"
    )

    rules_task = InfrastructureTask(
        agent=rules_agent,
        description="Evaluate business rules",
        expected_output="A list of matching rules and actions"
    )

    # Create and run the crew
    crew = Crew(
        agents=[
            CrewAIAgentAdapter(decision_agent),
            CrewAIAgentAdapter(rules_agent)
        ],
        tasks=[decision_task, rules_task],
        process=Process.sequential,
        verbose=True
    )

    result = await crew.kickoff(inputs={"test": "data"})
    print("Results:", result)

if __name__ == "__main__":
    asyncio.run(main())
```

## Documentation

For detailed documentation, please see:

- [API Reference](docs/api.md)
- [Advanced Usage](infrastructure/crewai/ADVANCED.md)
- [Examples](infrastructure/examples/)

## Examples

Check out the [examples](infrastructure/examples/) directory for complete examples:

- [Basic Integration](infrastructure/examples/crewai_integration_example.py) - Simple example of using infrastructure agents with CrewAI
- [Advanced Workflow](infrastructure/examples/advanced_crewai_integration.py) - Complex example with multiple agents and tasks

## Testing

To run the tests:

```bash
# Run unit tests
pytest tests/unit

# Run integration tests
pytest tests/integration

# Run all tests with coverage report
pytest --cov
```

---

## [Section: agents/infrastructure_crew/README.md]

# Infrastructure Crew Documentation

## 1. Overview

The Infrastructure Crew is a specialized group of agents responsible for managing and providing access to shared knowledge and core services within the broader agent ecosystem. Its primary function is to establish and maintain a comprehensive, flexible, and queryable Knowledge Graph (KG) representing various entities, relationships, and events relevant to the system's operations.

This crew leverages RDFLib for its knowledge representation, enabling semantic data modeling and powerful querying capabilities through SPARQL. The goal is to create a centralized, reliable source of truth that other agents and services can utilize for informed decision-making and context-aware operations.

## 2. Core Components

### 2.1. `CrewManager` (Located in `agents/infrastructure/`)

*   **Purpose**: The `CrewManager` acts as the central orchestrator for all agents, including those within the Infrastructure Crew. For the KG functionality, its key responsibilities include:
    *   Initializing and managing the lifecycle of the shared `rdflib.Graph` instance. This graph serves as the primary data store for the knowledge graph.
    *   Instantiating and providing the shared `rdf_graph` instance to relevant agents like the `KnowledgeGraphIngestionAgent` and `KnowledgeGraphQueryAgent`.
    *   Facilitating communication and coordination between agents.
*   **Interactions**: It passes the `rdf_graph` to KG agents upon their initialization, enabling them to operate on the same underlying data.

### 2.2. `KnowledgeGraphIngestionAgent` (`agents/infrastructure_crew/agents/knowledge_graph_ingestion_agent.py`)

*   **Purpose**: This agent is responsible for populating the RDF knowledge graph. It listens for events or receives data from various sources (e.g., other agents, external systems) and transforms this information into RDF triples, which are then added to the shared `rdf_graph`.
*   **Functionality**:
    *   Accepts an `rdf_graph` instance from the `CrewManager`.
    *   Uses predefined RDF namespaces, properties, and class types from `rdf_constants.py` to ensure consistency in data representation.
    *   Contains methods to create unique URIs for entities and relationships.
    *   Includes specific methods to add different types of entities (e.g., `Project`, `Task`, `Agent`, `AgentCrew`) and their properties to the graph.
    *   Provides `add_agent(agent_data: AgentSchema)` and `add_agent_crew(crew_data: AgentCrewSchema)` methods to ingest detailed information about individual agents and their crews, including various characteristics like reputation, skills, autonomy, and operational protocols.
*   **Interactions**: Receives data/events, processes them, and writes triples to the `rdf_graph` provided by `CrewManager`.

### 2.3. `KnowledgeGraphQueryAgent` (`agents/infrastructure_crew/agents/knowledge_graph_query_agent.py`)

*   **Purpose**: This agent provides the interface for querying the RDF knowledge graph. It allows other agents or services to retrieve information using the SPARQL query language.
*   **Functionality**:
    *   Accepts an `rdf_graph` instance from the `CrewManager`.
    *   Implements methods to execute SPARQL queries against the graph:
        *   `get_entity_by_id()`: Retrieves all properties of an entity given its original ID.
        *   `find_entities()`: Finds entities based on their type and specified property values.
        *   `get_related_entities()`: Finds entities related to a source entity, optionally filtering by relationship type and target entity type.
        *   `execute_raw_query()`: Allows execution of arbitrary SPARQL queries.
    *   Parses SPARQL query results into Python dictionaries for easier consumption.
*   **Interactions**: Receives query requests, executes them against the `rdf_graph`, and returns the results.

### 2.4. `LLMPoweredKnowledgeAgent` (`agents/infrastructure_crew/agents/llm_powered_knowledge_agent.py`)

*   **Purpose (Intended)**: This agent is designed to provide a natural language interface to the knowledge graph. Users or other agents could interact with it using plain English (or other languages) to ask questions or retrieve information, which the agent would then translate into appropriate KG queries (e.g., SPARQL).
*   **Current Status**: The initial version simulates LLM interactions. Full integration with the RDF graph for query generation and result interpretation is a future enhancement.
*   **Interactions (Intended)**: Would receive natural language queries, interact with the `KnowledgeGraphQueryAgent` (or directly with the `rdf_graph` via SPARQL) to fetch data, and then synthesize natural language responses.

### 2.5. `TaskOrchestrationAgent` (`agents/infrastructure_crew/agents/task_orchestration_agent.py`)

*   **Purpose**: This agent is responsible for managing the lifecycle of tasks within the system. This includes task creation, assignment, status tracking, and updates.
*   **Functionality**: Utilizes Pydantic models from `task_schemas.py` for defining task structures. It provides an API for task operations.
*   **Interactions**: Manages task data. While currently using in-memory storage, future enhancements could involve persisting task information into the RDF knowledge graph, allowing tasks to be linked with other entities like projects, products, or decisions.

## 3. Key Data Structures and Definitions

### 3.1. `rdf_constants.py` (`agents/infrastructure_crew/rdf_constants.py`)

*   **Purpose**: This file is crucial as it defines the shared vocabulary or ontology for the RDF knowledge graph. It contains:
    *   **Namespaces**: Standard RDF/RDFS/XSD namespaces and custom project-specific namespaces (e.g., `PROJECT_NS`).
    *   **Properties**: URIs for all properties used to describe entities (e.g., `NAME`, `STATUS`, `DESCRIPTION`, `ORIGINAL_ID`).
    *   **Entity Types**: URIs for classes or types of entities (e.g., `TYPE_PROJECT`, `TYPE_TASK`, `TYPE_AGENT`, `TYPE_AGENT_CREW`).
    *   **Agent/Crew Characteristic Properties**: A comprehensive set of URIs for describing attributes specific to agents and crews, such as `HAS_REPUTATION`, `USES_SHARED_MEMORY`, `HAS_COMMON_GOAL`, `IS_SELF_ORGANIZING`, `HAS_AUTONOMY_LEVEL`, `ENABLES_CONTINUOUS_LEARNING`, `HAS_RESILIENCE_MECHANISM`, `IS_INTEROPERABLE`, and `IS_COMPOSABLE`.
    *   **Relationship Types**: URIs for defining relationships between entities (e.g., `HAS_TASK`, `DEPENDS_ON`, `MEMBER_OF_CREW`, `HAS_MEMBER`).
*   **Importance**: Ensures consistency and interoperability of data within the KG. Both the ingestion and query agents rely heavily on these constants.

### 3.2. `schemas/knowledge_graph_schemas.py`

*   **Purpose**: Contains Pydantic models that define the conceptual structure and expected attributes for various entities that can be represented in the knowledge graph (e.g., `Project`, `Task`, `Product`, `AgentSchema`, `AgentCrewSchema`). The `AgentSchema` and `AgentCrewSchema` specifically model individual agents and groups of agents (crews), capturing their various characteristics and relationships.
*   **Usage**: While the primary storage and representation are RDF triples, these schemas serve as a clear definition of the data model, aid in data validation before ingestion, and can be used by agents when preparing data for the `KnowledgeGraphIngestionAgent` or interpreting results from the `KnowledgeGraphQueryAgent`.

### 3.3. `schemas/task_schemas.py`

*   **Purpose**: Contains Pydantic models specifically for task management, defining structures for `TaskDefinition`, `TaskStatus`, `TaskPriority`, etc.
*   **Usage**: Primarily used by the `TaskOrchestrationAgent` to manage and validate task-related data.

## 4. Interactions and Data Flow

1.  **Initialization**: The `CrewManager` starts and initializes an `rdflib.Graph` instance.
2.  **Agent Setup**: The `CrewManager` instantiates the `KnowledgeGraphIngestionAgent` and `KnowledgeGraphQueryAgent`, passing the shared `rdf_graph` to both.
3.  **Data Ingestion**: 
    *   External events or data from other agents are routed (potentially via `CrewManager` or directly) to the `KnowledgeGraphIngestionAgent`.
    *   The `KnowledgeGraphIngestionAgent` transforms this data into RDF triples using the vocabulary defined in `rdf_constants.py` and adds them to the shared `rdf_graph`.
4.  **Data Querying**:
    *   Agents or services requiring information from the KG send requests to the `KnowledgeGraphQueryAgent`.
    *   The `KnowledgeGraphQueryAgent` constructs and executes SPARQL queries (again, using `rdf_constants.py` for URIs) against the `rdf_graph`.
    *   Results are parsed and returned to the requester.
5.  **Task Management**: The `TaskOrchestrationAgent` manages tasks independently, with potential future integration for storing/linking task data within the main KG.
6.  **Natural Language Interaction (Future)**: The `LLMPoweredKnowledgeAgent` would translate user queries into SPARQL, use the `KnowledgeGraphQueryAgent` to fetch results, and then present them back to the user in natural language.

This RDF-centric approach allows for a flexible and extensible knowledge base, where new types of entities, properties, and relationships can be easily added by updating `rdf_constants.py` and the relevant agent logic, without requiring rigid schema migrations typical of traditional databases.

---

## [Section: agents/infrastructure_crew/infrastructure/README.md]

# Infrastructure Crew: Supply Chain & Inventory Management

## Overview

The Infrastructure Crew is the backbone of the agent-blockchain-integration system, specifically designed to manage complex supply chain and inventory operations. This document provides a comprehensive guide to the architecture, components, and workflows that power our intelligent supply chain management system.

## Architecture Overview

```
[Architecture diagram omitted for brevity]
```

## Core Components

### 1. Managers

Managers are the orchestrators of the infrastructure crew, responsible for high-level coordination and decision-making across the supply chain.

**Key Manager Types:**

1. **Inventory Manager**
   - Tracks stock levels across all warehouses
   - Manages reorder points and safety stock
   - Handles batch and serial number tracking
   - Coordinates with suppliers for replenishment

2. **Supply Chain Manager**
   - Oversees end-to-end supply chain operations
   - Manages relationships with suppliers and logistics providers
   - Optimizes routes and transportation modes
   - Handles disruptions and exceptions

3. **State Manager**
   - Maintains system-wide state consistency
   - Handles distributed transactions
   - Manages state versioning and conflict resolution
   - Provides real-time state snapshots

4. **Memory Manager**
   - Monitors and manages system memory usage
   - Handles memory pressure events
   - Implements cleanup strategies
   - Provides memory metrics and monitoring

5. **Team Memory Manager**
   - Manages memory allocation between teams
   - Implements memory sharing policies
   - Resolves memory conflicts
   - Provides team-level memory management

### Memory Management System

The Infrastructure Crew implements a sophisticated memory management system that operates at both system-wide and team-level scales. This system ensures efficient memory usage, prevents memory-related issues, and provides mechanisms for teams to share and manage memory resources effectively.

#### System-Wide Memory Management

The Memory Manager (`memory_manager.py`) handles system-wide memory monitoring and management:

1. **Memory Monitoring**
   - Continuous monitoring of system memory usage
   - Real-time memory pressure detection
   - Memory usage metrics collection
   - Automatic cleanup when pressure exceeds thresholds

2. **Memory Pressure Levels**
   - LOW (70%): Normal operation
   - MEDIUM (80%): Moderate cleanup
   - HIGH (90%): Aggressive cleanup
   - CRITICAL (95%): Emergency cleanup

3. **Cleanup Strategies**
   - Least Recently Used (LRU) eviction
   - State compression
   - Event cleanup
   - Cache invalidation

4. **Metrics and Monitoring**
   - Current memory usage
   - Peak memory usage

---

## [Section: agents/infrastructure_crew/infrastructure/crewai/README.md]

# CrewAI Integration for Infrastructure Agents

This module provides adapters and utilities to make infrastructure agents compatible with the [CrewAI](https://github.com/joaomdmoura/crewai) framework.

## Overview

The integration allows you to use your infrastructure agents (DecisionAgent, RulesAgent, AmbiguityAgent, StateAgent) within the CrewAI framework, enabling you to:

1. Use your existing agents in CrewAI workflows
2. Share tools between CrewAI and infrastructure agents
3. Leverage CrewAI's task orchestration capabilities
4. Maintain a consistent interface across your agent ecosystem

## Installation

```bash
# Install the required dependencies
pip install crewai pydantic pandas
```

## Usage

### Basic Example

```python
from infrastructure.agents import DecisionAgent, RulesAgent
from infrastructure.crewai import CrewAIAgentAdapter, InfrastructureTask
from crewai import Crew, Process

# Create your infrastructure agents
decision_agent = DecisionAgent(config={...})
rules_agent = RulesAgent(config={...})

# Create CrewAI-compatible tasks
decision_task = InfrastructureTask(
    agent=decision_agent,
    description="Make decisions based on the input data",
    expected_output="A list of decisions with confidence scores"
)

rules_task = InfrastructureTask(
    agent=rules_agent,
    description="Evaluate business rules",
    expected_output="A list of matching rules and actions"
)

# Create and run a crew
crew = Crew(
    agents=[
        CrewAIAgentAdapter(decision_agent),
        CrewAIAgentAdapter(rules_agent)
    ],
    tasks=[decision_task, rules_task],
    process=Process.sequential,
    verbose=True
)

result = await crew.kickoff(inputs={"event": {...}, "context": {...}})
```

### Using Tools

You can use CrewAI tools with your infrastructure agents:

```python
from infrastructure.crewai import create_csv_search_tool

# Create a CSV search tool
csv_tool = create_csv_search_tool(
    csv_path="data/sales.csv",
    description="Search sales data",
    examples=["Find top products by revenue", "Get sales by region"]
)

# Add the tool to your agent
decision_agent.tools = [csv_tool]

# The tool will be available in the agent's execute_task method
```

## API Reference

### CrewAIAgentAdapter

Adapter class that makes infrastructure agents compatible with CrewAI.

```python
CrewAIAgentAdapter(
    agent: BaseAgent,
    **kwargs
)
```

**Parameters:**
- `agent`: An instance of an infrastructure agent (e.g., DecisionAgent, RulesAgent)
- `**kwargs`: Additional arguments to pass to the CrewAIAgent constructor

### InfrastructureTask

A CrewAI task that works with infrastructure agents.

---

## [Section: agents/marketing/frontend/my-app/README.md]

This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.


## Overview

This project explores the integration of advanced AI agent systems with concepts potentially related to blockchain or decentralized collaboration. It features a sophisticated agent organization, including a federated learning system for collaborative model training and specialized QA agents for performance analysis.

## Agent Organization

The primary agent structure revolves around the `infrastructure_crew`, which serves as a central hub for various specialized agent functionalities.

### `infrastructure_crew`

Located at `agents/infrastructure_crew/`, this is the core crew responsible for foundational agent capabilities. It encompasses sub-crews and specialized agents that handle specific tasks.

Key sub-components and directories within `infrastructure_crew`:
*   **`agents/`**: This directory (`agents/infrastructure_crew/agents/`) houses the implementations of various specialized worker agents that perform specific tasks. Examples include `knowledge_graph_ingestion_agent.py`, `ambiguity_agent.py`, and `translation_qa_agent.py`.
*   **`qa_sub_crew/`**: (Formerly the top-level `qa_crew`) Located at `agents/infrastructure_crew/qa_sub_crew/`, this sub-crew is responsible for Quality Assurance tasks, primarily focused on evaluating project milestones. Its core agent, `QAAgent` (`agents/infrastructure_crew/qa_sub_crew/agents/qa_agent.py`), utilizes a federated learning system to improve its evaluation model.
*   **`translation_crew/`**: Located at `agents/infrastructure_crew/translation_crew/`, this sub-crew manages translation-related tasks. It likely orchestrates specialized translation agents (e.g., `inventory_translation_worker.py` found in `infrastructure_crew/agents/`).
*   **`tools/`**: Contains various tools used by the infrastructure agents, such as `FCEventSubscriberTool` and `FCPerformanceAnalyzerTool`.

### `TranslationQAAgent`

The `TranslationQAAgent` (defined in `agents/infrastructure_crew/agents/translation_qa_agent.py`) is a specialized QA agent. Its purpose is to:
*   Analyze the execution patterns and performance of the `TranslationCrew`.
*   Identify inefficiencies in the `TranslationCrew`'s planning, task decomposition, and internal information routing.
*   Utilize tools like `FCEventSubscriberTool` (to capture events from the `TranslationCrew`) and `FCPerformanceAnalyzerTool` (to analyze these events).
This agent provides meta-level QA by observing and reporting on the operational effectiveness of another agent crew.

## Service Registry and Discovery (`RegistryManagerAgent`)

The project includes a robust service registry and discovery mechanism, managed by the `RegistryManagerAgent` (located in `agents/infrastructure_crew/agents/registry_manager_agent.py`). This system allows agents and services to dynamically register their availability and capabilities, and for other components to discover and utilize them.

### Core Features:

1.  **Redis Backend**:
    *   The `RegistryManagerAgent` uses an asynchronous Redis client (`redis.asyncio.Redis`) as its persistent backend.
    *   Service information, crew-to-service mappings, and capability-to-service mappings are stored in Redis, ensuring scalability and data persistence.
    *   Specific key prefixes are used to organize data (e.g., `service_registry:service:<service_id>`).

2.  **Service Lifecycle Management**:
    *   **Registration (`register_service`)**:
        *   Services (e.g., other agents, tools) submit a `ServiceRegistrationRequest` (defined in `service_registry_schema.py`).
        *   The agent creates a `ServiceInfo` record, storing details like service ID, name, owning crew ID, offered capabilities, endpoint information, and registration/heartbeat timestamps.
        *   This `ServiceInfo` is stored in Redis. The service ID is also added to Redis sets associated with its `crew_id` and each of its `capabilities`.
    *   **Unregistration (`unregister_service`)**:
        *   Removes the service's primary record and its associations from the crew and capability sets in Redis.
    *   **Heartbeating (`handle_heartbeat`)**:
        *   Registered services are expected to periodically send `ServiceHeartbeat` messages.
        *   The `RegistryManagerAgent` updates the service's `last_heartbeat_at` timestamp and optionally its `status` (e.g., AVAILABLE, BUSY).
    *   **Stale Service Pruning (`_prune_stale_services`)**:
        *   A background monitoring task periodically checks for services that haven't sent a heartbeat within a configurable threshold (`DEFAULT_STALE_SERVICE_THRESHOLD_SECONDS`).
        *   Stale services are automatically unregistered to maintain an accurate registry of active services.

3.  **Service Discovery**:
    *   **By ID (`get_service_info`)**: Retrieve detailed information for a specific service if its ID is known.
    *   **By Crew (`find_services_by_crew`)**: Discover all services registered by a particular `crew_id`.
    *   **By Capability (`find_services_by_capability`)**: This is a key discovery method. Agents can query for services that offer a specific `capability` (e.g., "translation", "data_analysis"). The agent returns a list of all active services matching that capability.

4.  **Schema**:
    *   The system relies on Pydantic models defined in `agents/infrastructure_crew/schemas/service_registry_schema.py` for structuring service data (e.g., `ServiceInfo`, `ServiceRegistrationRequest`, `ServiceHeartbeat`, `ServiceStatus`).

### Usage:

The `CrewManager` (in `agents/infrastructure/crew_manager.py`) acts as a client to the `RegistryManagerAgent`, delegating service registration and unregistration requests, likely for services or agents spawned or managed by crews. Other agents within the system can then query the `RegistryManagerAgent` to find and interact with these registered services based on their needs.


## Contract Net Protocol and Task Marketplace

To facilitate dynamic task allocation and create a more adaptive multi-agent system, this project implements the Contract Net Protocol (CNP). This protocol allows agents to announce tasks, collect bids from capable worker agents, and award tasks based on bid evaluations, effectively creating a decentralized marketplace for tasks and services.

### 1. Contract Net Protocol (CNP) Implementation

The Contract Net Protocol provides a structured interaction pattern for task distribution and execution.

**Purpose:**
*   **Efficient Task Distribution**: Dynamically assign tasks to the most suitable available agents.
*   **Leveraging Specialization**: Enable agents with specific capabilities to bid for tasks they are well-suited to perform.
*   **Dynamic Resource Allocation**: Adapt to changing workloads and agent availability.

**Core Components & Flow:**

1.  **Task Initiator (`TaskOrchestrationAgent`):**
    *   Located in `agents/infrastructure_crew/agents/task_orchestration_agent.py`.
    *   Responsible for initiating tasks by broadcasting a **Call for Proposals (CFP)**.
    *   The CFP, defined by the `TaskAnnouncement` schema (see `agents/infrastructure_crew/schemas/contract_net_schemas.py`), details the task requirements, constraints, deadlines, and potentially the reward.
    *   Publishes CFPs to a designated Redis channel (e.g., `contract_net:cfp`).

2.  **Worker Agents (e.g., `BasicWorkerAgent`):**
    *   Specialized agents capable of performing tasks (e.g., `agents/infrastructure_crew/agents/basic_worker_agent.py`).
    *   Monitor the CFP channel for relevant task announcements.
    *   If a worker deems itself capable and willing to perform a task, it submits a **Bid**.
    *   Bids, defined by the `Bid` schema, include the worker's ID, the task ID, and any bid-specific information (e.g., proposed cost, estimated time, specific approach).
    *   Bids are sent to a Redis channel associated with the specific task or initiator (e.g., `contract_net:bids:<task_id>`).

3.  **Bid Evaluation and Task Awarding (by `TaskOrchestrationAgent`):**
    *   The `TaskOrchestrationAgent` collects bids for a defined period.
    *   It evaluates received bids based on criteria such as price, capability, estimated completion time, or other metrics.
    *   The task is awarded to the winning bidder. A `TaskAward` message is sent to the chosen worker.
    *   The winning worker acknowledges with a `TaskAcceptance` message. Other bidders may be notified that they were not selected.

4.  **Task Execution and Result Submission:**
    *   The awarded `WorkerAgent` executes the task.
    *   Upon completion, it submits the `TaskResult` (defined by the `TaskResult` schema) to the `TaskOrchestrationAgent`, typically via a dedicated Redis channel.

5.  **Confirmation and Completion:**
    *   The `TaskOrchestrationAgent` receives and processes the `TaskResult`.
    *   It may perform validation and then formally closes the task.
    *   (Future Scope: Integration with a payment or reputation system based on successful task completion).

**Communication Backbone:**
*   Redis streams or pub/sub channels are extensively used for:
    *   Broadcasting CFPs.
    *   Submitting bids.
    *   Sending task awards and acceptances.
    *   Delivering task results.

**Schemas:**
*   All data structures for the CNP interactions (e.g., `TaskAnnouncement`, `Bid`, `TaskAward`, `TaskResult`) are defined using Pydantic models in `agents/infrastructure_crew/schemas/contract_net_schemas.py`.

### 2. Agent Marketplace Functionality

The implementation of the Contract Net Protocol naturally gives rise to an agent marketplace.

**Concept:**
*   An environment where agents (task initiators) can "advertise" tasks needing completion, and other agents (workers) can "offer" their services by bidding on these tasks.
*   This fosters a competitive and efficient allocation of resources based on supply and demand for agent capabilities.

**Interaction with CNP:**
*   The CNP provides the fundamental mechanism for this marketplace: CFPs are the "demand," and bids represent the "supply."

**Synergy with Service Registry:**
*   The `RegistryManagerAgent` can play a crucial role:
    *   Worker agents can register their capabilities (e.g., "translation," "data_analysis," "code_generation") with the `RegistryManagerAgent`.
    *   `TaskOrchestrationAgents` could potentially query the registry to identify potentially capable agents and target CFPs more effectively or use this information during bid evaluation.
    *   Worker agents could use the registry to discover `TaskOrchestrationAgents` or filter CFPs based on their registered capabilities.

**Recent Developments & Testing:**
*   The `TaskOrchestrationAgent` has been enhanced with `_initialize` and `_process` methods to support its role in the CNP.
*   The `BasicWorkerAgent` serves as an initial example of a bidding agent.
*   The entire flow is intended to be tested using scripts like `run_contract_net_test.py` to simulate task announcements, bidding, awarding, and execution.

**Future Enhancements:**
*   More sophisticated bidding strategies for worker agents.
*   Advanced evaluation criteria for task initiators.
*   Integration of reputation systems for agents based on their performance in the marketplace.
*   Mechanisms for negotiation between initiators and bidders.


## Advanced Memory Management System

The project incorporates a sophisticated memory management system designed to provide efficient, flexible, and observable memory allocation and sharing for agents and teams. This system is crucial for managing resources in a multi-agent environment, ensuring stability and performance.

### Core Components:

*   **`MemoryManager` (`agents/infrastructure/memory/memory_manager.py`)**:
    *   Manages overall system memory, monitors usage, and handles memory pressure scenarios.
    *   Responsible for periodic cleanup of stale or unused memory resources.
    *   Emits system-wide memory events (e.g., `MemoryPressureWarningEvent`, `MemoryCleanupInitiatedEvent`).
*   **`TeamMemoryManager` (`agents/infrastructure/memory/team_memory_manager.py`)**:
    *   Manages memory allocation and quotas for different teams of agents.
    *   Facilitates dynamic memory sharing between teams.
    *   Emits team-specific memory events (e.g., `TeamMemoryAllocationSuccessEvent`, `TeamMemorySharingCompletedEvent`).

### Key Features & Design Principles:

1.  **Standardized Pydantic Models**:
    *   All core data structures related to memory, such as `TeamMemory` (representing a team's memory state) and `TeamMemoryInfo` (for context sharing), are defined using Pydantic models (`agents/infrastructure_crew/schemas/context_schemas.py` and `agents/infrastructure/memory/team.py`).
    *   This ensures data validation, clear schemas, and improved interoperability across the system.

2.  **Standardized Event-Driven Architecture**:
    *   All memory-related operations (allocation, deallocation, sharing, conflict detection, pressure warnings, cleanup actions) trigger standardized events.
    *   These events, defined as Pydantic models in `agents/infrastructure_crew/schemas/event_schemas.py` (e.g., `TeamMemoryAllocationSuccessEvent`, `MemoryPressureWarningEvent`), inherit from a common `BaseEvent`.
    *   This allows for robust and decoupled communication, making it easier to monitor, debug, and extend memory management functionalities.

3.  **Redis Integration**:
    *   Redis is utilized for:
        *   Distributing memory-related events via pub/sub channels, enabling real-time updates and reactions from interested components.
        *   Persisting the state of `TeamMemory` objects (serialized as JSON strings), ensuring data durability and consistency for team memory allocations.

4.  **Team-Based Quotas and Priorities**:
    *   The `TeamMemoryManager` allows for the definition of memory quotas for different teams, potentially with varying priority levels, enabling fine-grained resource control.

5.  **Dynamic Memory Sharing**:
    *   Mechanisms are in place for teams to request and share memory quotas dynamically, promoting efficient resource utilization.

6.  **Centralized Monitoring and Cleanup**:
    *   The `MemoryManager` provides a centralized point for monitoring overall memory usage and can initiate cleanup procedures when memory pressure is detected or during periodic maintenance.

### Benefits:

*   **Improved Interoperability**: Standardized models and events simplify integration between different agents and services.
*   **Enhanced Data Integrity**: Pydantic models enforce data validation, reducing errors.
*   **Increased Maintainability**: Clear schemas and decoupled event-driven design make the system easier to understand, modify, and extend.
*   **Better Observability**: Standardized events provide clear signals for monitoring and debugging memory-related operations throughout the agent ecosystem.


## MARL-based Inventory and Marketing Optimization

The project includes a Multi-Agent Reinforcement Learning (MARL) system designed to optimize inventory management and marketing strategies for a portfolio of SKUs. This system is located within the `federated_learning/` directory.

### Core Components:

1.  **Inventory and Marketing Simulation Environment (`InventoryMarketingSim`)**:
    *   **File**: `federated_learning/marl_environment.py`
    *   **Functionality**: Simulates the day-to-day operations of managing multiple SKUs, including sales, inventory replenishment, holding costs, shortage costs, and the impact of promotional activities.
    *   **Dynamic SKU Data Loading**: SKU configurations (e.g., unit cost, price, demand parameters, lead times, initial inventory, promotion effects, capacity) are loaded dynamically from a CSV file (`federated_learning/sample_sku_data.csv`) using the `load_sku_configs_from_csv` method. This allows for easy experimentation with diverse and realistic product data.

2.  **MARL Trainer (`InventoryMarketingMARLTrainer_CTDE`)**:
    *   **File**: `federated_learning/marl_trainer.py`
    *   **Architecture**: Implements a Centralized Training with Decentralized Execution (CTDE) approach. For each SKU, two agents are trained:
        *   An **Inventory Agent**: Decides on reorder quantities.
        *   A **Marketing Agent**: Decides on promotion levels (percentage discount).
    *   **State Discretization**:
        *   The continuous state variables from the simulation (inventory level, average sales, outstanding orders, current promotion percentage) are discretized into bins to make them suitable for Q-learning.
        *   The bins for inventory, sales, orders, and promotions have been refined based on realistic SKU data ranges to improve learning effectiveness. The state tuple for each SKU is `(inv_bin, sales_bin, orders_bin, promo_bin)`.
    *   **Learning Algorithm**: Uses Q-learning for each agent.
    *   **Policy Management**: Trained Q-table policies can be saved locally. Integration with the `RegistryManagerAgent` (via `SharableLearning` objects) allows for publishing these policies, enabling potential sharing and reuse across the wider agent ecosystem.

### Key Features & Recent Enhancements:

*   **Realistic Simulation**: The use of CSV-loaded SKU data makes the simulation environment more representative of real-world scenarios.
*   **Refined State Representation**: Improved discretization bins for state variables, including the addition of promotion discretization, aim to enhance the MARL agents' learning process.
*   **Modular Design**: The simulation environment and the MARL trainer are distinct components, facilitating independent development and testing.
*   **Extensibility**: The system is designed to be extensible, for example, by incorporating more complex demand models or agent interactions.


## Federated Learning System for `QAAgent`

A federated learning (FL) system is implemented to train the model parameters of the `QAAgent` (located in `agents/infrastructure_crew/qa_sub_crew/agents/qa_agent.py`). This allows multiple `QAAgent` clients to collaboratively refine a global model without sharing their local data, enhancing privacy and enabling learning from diverse datasets.

### Architecture

The FL system consists of:
1.  **Federated Learning Server (`federated_learning/server.py`)**:
    *   Orchestrates the federated learning process.
    *   Initializes the global model parameters.
    *   Aggregates model updates received from clients.
    *   Manages rounds of training and evaluation.
2.  **Federated Learning Client (`federated_learning/run_qa_client.py`)**:
    *   Wraps an instance of the `QAAgent`.
    *   Receives the global model from the server.
    *   Performs local training/updates using the `QAAgent`'s local data and logic.
    *   Sends its updated model parameters back to the server.
    *   Evaluates the global model using the `QAAgent`'s evaluation logic.
3.  **`QAAgent` Federated Learning Methods**:
    *   `get_federated_parameters()`: Provides the agent's current model parameters to the FL client.
    *   `set_federated_parameters()`: Updates the agent's model parameters with those received from the server.
    *   `perform_local_update_and_get_parameters()`: Simulates a local training step and returns updated parameters.
    *   `evaluate_global_parameters()`: Evaluates the received global model parameters.

### Parameter Handling

*   **Initialization**: The server starts with default initial parameters (`[0.1, 0.1, 0.1]`) if no saved model is found.
*   **Loading**: If a `final_federated_model.npz` file exists in the project root, the server loads the parameters from this file to initialize the global model.
*   **Saving**: The server uses a custom Flower strategy, `FedAvgWithSaving` (defined in `server.py`), to save the aggregated global model parameters to `final_federated_model.npz` after each successful `fit` round (training round). This ensures the latest trained model is persisted.

### Evaluation Metrics

The `QAAgent.evaluate_global_parameters()` method calculates:
*   **Loss**: Mean Squared Error (MSE) between the received global parameters and a predefined set of `ideal_federated_parameters` within the `QAAgent`.
*   **Accuracy**: Derived from the MSE as `1.0 - sqrt(loss)`, ensuring the value is clipped between 0.0 and 1.0. This provides a measure of how close the current global model is to the ideal parameters.

### How to Run the Federated Learning System

1.  **Prerequisites**:
    *   Ensure Python 3.x is installed.
    *   Install necessary dependencies. Key dependencies include `flwr` (Flower for federated learning) and `numpy`. You might need to install them via pip:
        ```bash
        pip install flwr numpy
        # Add other dependencies if specified in a requirements.txt
        ```
2.  **Start the Server**:
    Open a terminal, navigate to the project root (`agent_blockchain-integration-main`), and run:
    ```bash
    python federated_learning/server.py
    ```
    The server will start and wait for clients. By default, it listens on `127.0.0.1:8081`.

3.  **Start Client(s)**:
    Open one or more new terminals. For each client, navigate to the project root and run:
    ```bash
    python federated_learning/run_qa_client.py --crew_id="unique_client_alpha"
    ```
    Replace `"unique_client_alpha"` with a unique ID for each client (e.g., `"client_beta"`, `"client_gamma"`).
    Clients will connect to the server, participate in training rounds, and send their updates.

    The server is configured for a set number of rounds (e.g., 3). After completion, the server will shut down, and the `final_federated_model.npz` file will contain the trained parameters.

## Event-Driven Evaluation and Reward System

Beyond federated learning for model parameter refinement, the `QAAgent` also operates within a sophisticated event-driven evaluation and reward system. This system provides a feedback loop based on the performance of agent crews executing tasks.

### 1. Event Capture (`FCEventSubscriberTool`)

*   **Mechanism**: The `FCEventSubscriberTool` (located in `agents/infrastructure_crew/tools/`) captures detailed operational data from crew executions.
*   **Process**: Using a `crew_step_logger_callback`, it logs agent actions (tool usage, inputs, observations) and final agent outputs.
*   **Output**: Events are stored in-memory, keyed by a `crew_run_id`, and can be retrieved as a JSON string, providing a raw transcript of a crew's operations.

### 2. Performance Analysis (`FCPerformanceAnalyzerTool`)

*   **Mechanism**: The `FCPerformanceAnalyzerTool` (also in `agents/infrastructure_crew/tools/`) processes the raw event data from the `FCEventSubscriberTool`.
*   **Process**: It analyzes event sequences to calculate comprehensive performance metrics, including task durations, agent execution times, tool usage statistics, and error counts.
*   **Output**: It generates a `PerformanceAnalysisReport` (JSON string and Markdown format) that summarizes:
    *   Overall crew performance metrics.
    *   Breakdown of individual task performance.
    *   Performance summaries for each agent and tool involved.
    *   A list of identified errors.
*   **Implicit Penalties**: The tool flags operations that exceed predefined thresholds (e.g., for task duration, agent/tool error rates, average execution times). While not assigning direct numerical penalties, these flags, along with error reports, serve as negative feedback by highlighting areas of underperformance.

### 3. Reward Evaluation (`QAAgent` and `milestones_config.yaml`)

*   **Mechanism**: The `QAAgent` (in `agents/infrastructure_crew/qa_sub_crew/agents/`) uses the `PerformanceAnalysisReport` and a configuration of predefined objectives to grant rewards.
*   **Milestones**: Reward criteria are defined in `agents/infrastructure_crew/qa_sub_crew/config/milestones_config.yaml`. Milestones include:
    *   `TaskCompletionMilestone`: Rewards for successfully completing specific tasks within defined error limits.
    *   `CrewPerformanceMilestone`: Rewards for overall crew efficiency (e.g., low total duration, minimal errors, number of tasks completed).
    *   `ExternalStateMilestone`: Rewards for verifying that external systems (e.g., mock Blockchain, Database, API endpoints) are in an expected state. This involves the `QAAgent` using specialized (currently mock) tools to query these systems.
*   **Process**: The `QAAgent`'s `evaluate_and_reward` method compares the data in the `PerformanceAnalysisReport` and the outcomes of external state queries against the conditions specified in each milestone.
*   **Outcome**: If a milestone's criteria are met, a corresponding `reward_amount` is granted (currently simulated via `_mock_grant_reward`). Rewards are withheld if performance or state conditions do not meet the milestone requirements, effectively penalizing suboptimal outcomes.

### 4. Connection to Learning and Adaptation

The rewards (or lack thereof) generated by this system serve as a crucial feedback signal. For the `QAAgent`, these signals are intended to inform the adjustments of its `federated_parameters` during the federated learning process. This creates a loop where the agent's internal model is refined based on its ability to accurately assess and achieve performance objectives, driving adaptation towards more effective evaluation and potentially guiding the improvement of the crews being assessed.

I. Overall Architecture & Message Flow

The system is designed for a multi-agent environment where tasks are initiated, orchestrated, and executed by various components.

Initiation: Work can enter the system in several ways:
An external trigger (e.g., an API call, a message dropped into a specific Redis queue by another application, a scheduled job) that a standalone worker or swarm manager is listening to.
An internal event generated within CrewManager itself (e.g., by a monitoring agent).
An explicit call to CrewManager.distribute_event() from some part of the application that has access to the CrewManager instance.
CrewManager as Central Orchestrator (for Internal Events & Task Dispatch):
If work starts as an Event within CrewManager, it's placed on an internal asyncio.PriorityQueue.
CrewManager's internal agents process these events.
A key internal agent, the TaskOrchestrationAgent, is responsible for taking certain events and translating them into messages that are then published to external Redis queues.
Redis as the External Message Broker:
Redis lists are used as message queues for tasks destined for external workers or swarms.
Redis pub/sub might be used for broader notifications (e.g., by swarm managers or for service discovery updates).
Redis keys/hashes are used for service registration and potentially state management.
External Workers & Swarms (Consumers & Further Producers):
Standalone Workers (e.g., CornFlakesWorker, promotional_translation_worker.py): These are independent Python processes that listen to specific Redis queues using blocking operations (like BLPOP). Upon receiving a message, they typically execute a high-level functional crew (e.g., SalesToPromotionalTranslationCrew) and may then push results to other Redis queues (e.g., an api_queue or a queue for the next stage of processing).
Swarm Architectures (e.g., ProductSwarmManager): These are also independent processes that manage a collection of more specialized agents (often built with crewai). They listen to Redis queues or pub/sub channels for tasks/triggers. They orchestrate their internal swarm and publish outputs to Redis queues.
High-Level Functional Crews (Business Logic Units):
(e.g., MarketingCrew, InventoryCrew, SalesToInventoryTranslationCrew): These encapsulate the logic for specific business tasks, usually by defining a set of crewai agents and tasks. They are not directly run by CrewManager's main event loop. Instead, they are instantiated and executed by the standalone workers or swarm managers when those components receive a relevant task message from Redis.
II. CrewManager - The Central Orchestrator

The CrewManager class is the heart of the infrastructure, managing internal agents, an internal event bus, and providing centralized services. It does not directly manage the lifecycle of external worker processes but facilitates communication with them.

init(self, config: Dict[str, Any]):
Stores the provided config.
Initializes dictionaries for agents (internal agents it manages) and agent_health.
Sets up redis_pool (initially None), an event_queue (asyncio.PriorityQueue), and a metrics dictionary.
Initializes logger and a _shutdown flag.
Declares placeholders for various internal agents (e.g., registry_manager_agent, task_orchestration_agent).
Initializes MemoryManager and TeamMemoryManager for shared memory capabilities.
Populates the metrics dictionary with initial keys for tracking various counts and states.
async def initialize(self): This is a critical setup method.
Initializes an rdf_graph (instance of rdflib.Graph).
Redis Connection: Establishes a connection pool to Redis (aioredis.Redis) using configuration for URL, max connections, and timeout. This redis_pool is passed to internal agents that need it.
Internal Agent Initialization & Startup: It proceeds to initialize and start a suite of internal infrastructure agents. For each:
A configuration dictionary is prepared.
The agent class is instantiated.
agent.initialize() is called.
agent.start() is called (many agents have this to begin their operations, like listening to Redis or starting internal tasks).
Successfully initialized agents are often added to self.agents dictionary, keyed by their agent_id.
Agents Initialized:
RegistryManagerAgent: For service registration and discovery using Redis.
SchemaValidatorAgent: For validating data against predefined schemas.
SystemMonitorAgent: (Its initialization was partially commented out or incomplete in snippets, but it's intended for monitoring system health).
KnowledgeGraphIngestionAgent: Ingests data into the rdf_graph, potentially using Redis for coordination or data sourcing. Added to self.agents.
KnowledgeGraphQueryAgent: Queries the rdf_graph. Added to self.agents.
LLMPoweredKnowledgeAgent: Interacts with the knowledge graph agents using an LLM. Added to self.agents.
TaskOrchestrationAgent: Crucial for message brokering. Receives the redis_pool. This agent is responsible for dispatching tasks to external Redis queues. Added to self.agents.
ExampleWorkerAgent: An example of an internal worker agent that can process events directly. Added to self.agents.
StateAgent: (Implicitly used by get_state/set_state. Its explicit initialization wasn't fully detailed in the viewed snippets but is a logical component).
If critical agents like RegistryManagerAgent fail to initialize, it can raise a RuntimeError.
async def add_agent(self, agent: BaseAgent):
Registers a new internal agent with the CrewManager.
Checks for duplicate agent names.
Assigns self.redis_pool to the agent.
Initializes health tracking for the agent (AgentHealth object).
Calls agent.initialize() and updates its state to READY or ERROR.
async def distribute_event(self, event: Event):
This is the primary method for introducing work into CrewManager's internal event system.
Puts the Event object onto self.event_queue (an asyncio.PriorityQueue).
Increments metrics["event_count"].
If not already running, it creates an asyncio.task for self._process_events() to start consuming from the queue.
async def _process_events(self):
The core internal event loop. Runs continuously while CrewManager is not shutting down.
Waits for and gets an Event from self.event_queue.
Iterates through all registered internal agents in self.agents.values().
For each agent, it calls agent.can_handle_event(event).
If an agent can handle the event, agent.process_event(event) is called. This is where agents like TaskOrchestrationAgent would do their work (e.g., push to Redis).
Handles errors during event processing and updates metrics["error_count"].
async def _health_monitor(self):
A background task that runs periodically.
Updates the health status of internal agents (e.g., checking for liveness timeouts).
Updates various metrics: agent health, memory usage (from MemoryManager and TeamMemoryManager), Redis connection status, and total registered services (by querying keys from RegistryManagerAgent's prefix in Redis).
Optionally, it can persist these metrics (e.g., using the StateAgent).
Service Registry Methods (delegated to RegistryManagerAgent via events or direct calls if RegistryManagerAgent exposes them):
async def register_service(self, registration_request: ServiceRegistrationRequest)
async def unregister_service(self, service_id: str)
async def get_service_info(self, service_id: str)
async def find_services_by_crew(self, crew_id: str)
async def find_services_by_capability(self, capability: str)
async def handle_service_heartbeat(self, heartbeat: ServiceHeartbeat)
These methods interact with the RegistryManagerAgent (which uses Redis) to manage a directory of available services/agents in the ecosystem.
Schema Validation Methods (delegated to SchemaValidatorAgent):
async def validate_data_against_schema(self, data: Dict[str, Any], schema_identifier: str, is_event_type: bool = False)
async def get_event_schema(self, event_type: str)
These interact with SchemaValidatorAgent to ensure data conforms to expected structures.
State Management Methods (likely via an internal StateAgent):
async def get_state(self, key: str) -> Optional[Any]: Retrieves a value from a persistent state store (likely Redis).
async def set_state(self, key: str, value: Any, ttl: Optional[int] = None) -> bool: Sets a value in the state store.
async def get_snapshot(self) -> Dict[str, Any]: Provides a snapshot of current metrics, agent health, and state keys.
Getter Methods for Internal Agents:
get_knowledge_graph_ingestion_agent(), get_knowledge_graph_query_agent(), get_llm_powered_knowledge_agent(), get_task_orchestration_agent(), get_example_worker_agent(): Provide access to these initialized internal agents.
async def shutdown(self):
Sets the _shutdown flag to True.
Cancels background tasks like _event_processor_task and _health_monitor_task.
Iterates through all internal agents in self.agents and calls their stop() or shutdown() methods.
Specifically calls stop() on RegistryManagerAgent, SchemaValidatorAgent, and SystemMonitorAgent if they are initialized.
Closes the Redis connection pool (self.redis_pool.close()).
III. Key Internal Infrastructure Agents (Managed by CrewManager)

TaskOrchestrationAgent:
Role: This is the primary bridge between CrewManager's internal event system and the external Redis-based messaging system used by workers and swarms.
Operation:
It's an internal agent registered with CrewManager.
Its can_handle_event(event) method determines if an incoming event is something it should process (e.g., an event type indicating a task needs to be dispatched externally).
Its process_event(event) method contains the logic to:
Parse the event data.
Determine the target Redis queue (e.g., corn_flakes_queue, marketing_campaign_queue) based on the event type or data.
Format the message payload (typically JSON).
Use the redis_pool (provided by CrewManager) to RPUSH the message onto the appropriate Redis list (queue).
This agent effectively translates internal CrewManager events into external Redis messages.
RegistryManagerAgent:
Manages service registration, unregistration, heartbeats, and discovery. Services (which can be other agents, crews, or capabilities) register themselves with metadata. Other components can then query the registry to find available services. It uses Redis to store this information (e.g., under keys with a specific prefix).
SchemaValidatorAgent:
Provides a centralized way to validate data structures (e.g., event payloads, API requests/responses) against predefined schemas (likely JSON Schemas or Pydantic models).
Knowledge Graph Agents (KnowledgeGraphIngestionAgent, KnowledgeGraphQueryAgent, LLMPoweredKnowledgeAgent):
Manage interactions with an RDF knowledge graph. Ingestion adds data, Query retrieves it, and LLMPowered provides a natural language interface or more complex reasoning over it.
ExampleWorkerAgent:
Serves as a template or an actual internal worker that processes certain events directly within the CrewManager's event loop, without dispatching them externally.
StateAgent (Implied/Not Fully Detailed in Snippets):
Would be responsible for abstracting interactions with a persistent key-value store (likely Redis) for CrewManager's state management needs (get_state, set_state).
IV. External Components (Independent Processes)

These components run as separate processes and interact with the system primarily through Redis.

Standalone Workers (e.g., promotional_translation_worker.py, inventory_translation_worker.py, CornFlakesWorker):
Role: Execute specific, often long-running, tasks or business logic.
Operation:
Connect directly to Redis.
Listen to one or more dedicated Redis list queues using BLPOP (blocking list pop).
When a message (pushed by TaskOrchestrationAgent) is received:
Deserialize the message (usually JSON).
Instantiate and run a corresponding High-Level Functional Crew (e.g., SalesToPromotionalTranslationCrew is run by promotional_translation_worker.py).
The crew performs its defined tasks.
The worker takes the output from the crew.
It may then RPUSH this result to another Redis queue (e.g., api_queue for external exposure, or a queue for the next stage in a multi-step workflow).
They are self-contained and their lifecycle is managed outside of CrewManager.
Swarm Architecture (e.g., ProductSwarmManager):
Role: Orchestrates a group of specialized agents (a "swarm," often using crewai or similar) to accomplish a more complex, collaborative task.
Operation:
Runs as an independent process.
Connects to Redis.
Listens to specific Redis queues (for tasks) or subscribes to Redis pub/sub channels (for triggers/events). These tasks/events are typically published by CrewManager's TaskOrchestrationAgent.
Manages the lifecycle and communication within its internal swarm of agents.
The ProductSwarmManager's leader_callback, for example, shows it pushing the leader agent's output to an api_queue in Redis.
Swarm components might also publish intermediate results or requests for other services to other Redis queues.
V. High-Level Functional Crews

Examples: MarketingCrew, InventoryCrew (though its file location is problematic as per MEMORY[46ea90be-74ee-4f03-a6d3-433ace1b7674]), SalesToInventoryTranslationCrew, CornFlakesCrew.
Role: These are the primary units of business logic execution. They are typically built using the crewai library, defining a set of specialized AI agents and the tasks they need to perform in sequence or collaboration.
Invocation:
They are not directly instantiated or run by CrewManager's main event loop.
They are instantiated and "kicked off" by:
Standalone workers (e.g., promotional_translation_worker.py creates and runs SalesToPromotionalTranslationCrew).
Swarm managers (which might internally use crewai to define their swarm members and their collective tasks).
Interaction with Redis: They generally don't interact with Redis directly. The worker/swarm manager that runs them handles Redis communication for receiving tasks and publishing results.
VI. The InventoryCrew Discrepancy (MEMORY[46ea90be-74ee-4f03-a6d3-433ace1b7674])

The CrewManager.py imports InventoryCrew, suggesting an intent for CrewManager to interact with it. However, the file agents/inventory_crew/inventory_crew.py was reported as not found. If InventoryCrew were correctly integrated:

It might be instantiated and run by an internal agent within CrewManager (perhaps TaskOrchestrationAgent or a dedicated "functional crew runner" agent) when a specific type of event is processed. The output of InventoryCrew would then likely become a new event for CrewManager.distribute_event(), or its results directly used by the TaskOrchestrationAgent to dispatch further sub-tasks to Redis.
Alternatively, InventoryCrew might be designed to be run by its own dedicated standalone worker, similar to promotional_translation_worker.py.
The missing file prevents a complete understanding of how inventory-related tasks are meant to be handled within this architecture.

Summary of Message Brokering:

Internal: CrewManager uses an asyncio.PriorityQueue (event_queue) as an internal event bus. distribute_event adds to it, and _process_events consumes from it, routing events to internal agents.
External Bridge: The TaskOrchestrationAgent (an internal agent) is the key component that bridges the internal event bus to the external Redis messaging system. It consumes internal events and publishes messages to Redis lists (queues).
External: Standalone workers and swarm managers are independent processes that consume messages from these Redis queues (BLPOP) and, after processing (often by running a functional crew), publish results to other Redis queues (RPUSH).
This detailed structure provides a comprehensive view of how messages are brokered and tasks are managed across the different components of your multi-agent system. The system is flexible, allowing for both tightly coupled internal agent interactions within CrewManager and loosely coupled, scalable task processing via external workers and swarms using Redis.

## Project Structure Highlights

agent_blockchain-integration-main/
├── agents/
│   └── infrastructure_crew/
│       ├── agents/                 # Specialized agent implementations (e.g., translation_qa_agent.py)
│       ├── qa_sub_crew/            # QA sub-crew
│       │   ├── agents/
│       │   │   └── qa_agent.py     # Core QAAgent with FL capabilities
│       │   └── config/
│       │       └── milestones_config.yaml
│       ├── translation_crew/       # Translation sub-crew
│       │   └── translation_crew.py
│       └── tools/                  # Tools for infrastructure agents
├── federated_learning/
│   ├── server.py                   # FL Server
│   └── run_qa_client.py            # FL Client script
├── README.md                       # This file
└── final_federated_model.npz       # Stores trained FL model parameters (created after FL run)

## Contributing

Details on contributing to this project will be added here.

## License

Specify project license information here.
