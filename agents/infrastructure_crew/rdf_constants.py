from rdflib import Namespace, RDF, RDFS, XSD

# Base namespace for our project's ontology
PROJECT_NS_STR = "http://example.com/ontology/agent_project/"
PROJECT_NS = Namespace(PROJECT_NS_STR)

# Namespace for Agent-specific concepts
AGENT_NS_STR = "http://example.com/ontology/agent/"
AGENT_NS = Namespace(AGENT_NS_STR)

# Namespace for Agent Crew-specific concepts
AGENT_CREW_NS_STR = "http://example.com/ontology/agent_crew/"
AGENT_CREW_NS = Namespace(AGENT_CREW_NS_STR)

# Namespace for Characteristics
CHARACTERISTIC_NS_STR = "http://example.com/ontology/characteristic/"
CHARACTERISTIC_NS = Namespace(CHARACTERISTIC_NS_STR)

# Namespace for Relationships
RELATIONSHIP_NS_STR = "http://example.com/ontology/relationship/"
RELATIONSHIP_NS = Namespace(RELATIONSHIP_NS_STR)

# Common properties we'll use
NAME = PROJECT_NS.name
DESCRIPTION = PROJECT_NS.description
STATUS = PROJECT_NS.status
PRIORITY = PROJECT_NS.priority
START_DATE = PROJECT_NS.startDate
END_DATE = PROJECT_NS.endDate
DATA = PROJECT_NS.data # For generic JSON data
ENTITY_TYPE_PROP = PROJECT_NS.entityType # To store the original Pydantic model type (e.g., "Project", "Task")
ORIGINAL_ID = PROJECT_NS.originalId # To store the original UUID or string ID from Pydantic model
CREATED_AT = PROJECT_NS.createdAt
UPDATED_AT = PROJECT_NS.updatedAt
REPOSITORY_URL = PROJECT_NS.repositoryUrl
CURRENT_MILESTONE = PROJECT_NS.currentMilestone
BUDGET = PROJECT_NS.budget
PROJECT_HAS_MANAGER = PROJECT_NS.hasManager

# Relationships
HAS_TASK = PROJECT_NS.hasTask
PART_OF_PROJECT = PROJECT_NS.partOfProject
DEPENDS_ON = PROJECT_NS.dependsOn
MEMBER_OF_CREW = PROJECT_NS.memberOfCrew
HAS_MEMBER = PROJECT_NS.hasMember

# Entity Types (Classes in our ontology)
TYPE_PROJECT = PROJECT_NS.Project
TYPE_TASK = PROJECT_NS.Task
TYPE_PRODUCT = PROJECT_NS.Product
TYPE_MARKET_SIGNAL = PROJECT_NS.MarketSignal
TYPE_PERFORMANCE_METRIC = PROJECT_NS.PerformanceMetric
TYPE_DECISION = PROJECT_NS.Decision
TYPE_OUTCOME = PROJECT_NS.Outcome
TYPE_AGENT = PROJECT_NS.Agent
TYPE_AGENT_CREW = PROJECT_NS.AgentCrew

# Agent/Crew Characteristics and Properties
HAS_REPUTATION = PROJECT_NS.hasReputation # Could be a literal (e.g., score) or link to a reputation object
USES_SHARED_MEMORY = PROJECT_NS.usesSharedMemory # Could be a link to a memory store URI or description
HAS_COMMUNICATION_PROTOCOL = PROJECT_NS.hasCommunicationProtocol # Description or link to protocol docs
HAS_COMMON_GOAL = PROJECT_NS.hasCommonGoal # Textual description or link to goal definition
HAS_SKILL_DIVERSITY = PROJECT_NS.hasSkillDiversity # Textual description or list of skills
IS_SELF_ORGANIZING = PROJECT_NS.isSelfOrganizing # Boolean or descriptive
HAS_AUTONOMY_LEVEL = PROJECT_NS.hasAutonomyLevel # Descriptive (e.g., high, medium, low, or specific rules)
ENABLES_CONTINUOUS_LEARNING = PROJECT_NS.enablesContinuousLearning # Boolean or descriptive
EXHIBITS_ADAPTATION = PROJECT_NS.exhibitsAdaptation # Boolean or descriptive
HAS_RESILIENCE_MECHANISM = PROJECT_NS.hasResilienceMechanism # Descriptive
HAS_FAULT_TOLERANCE = PROJECT_NS.hasFaultTolerance # Descriptive or boolean
HAS_TRANSPARENT_INCENTIVES = PROJECT_NS.hasTransparentIncentives # Boolean or link to incentive model
HAS_GOVERNANCE_MODEL = PROJECT_NS.hasGovernanceModel # Link to governance docs or description
IS_INTEROPERABLE = PROJECT_NS.isInteroperable # Boolean or description of standards met
IS_COMPOSABLE = PROJECT_NS.isComposable # Boolean or description of how it can be combined
INTEROPERABILITY_DESCRIPTION = PROJECT_NS.interoperabilityDescription # Detailed text about interoperability
COMPOSABILITY_DESCRIPTION = PROJECT_NS.composabilityDescription # Detailed text about composability
SKILLS_DESCRIPTION = PROJECT_NS.skillsDescription # Detailed text about skills

# Standard RDF namespaces for convenience
RDF_NS = RDF
RDFS_NS = RDFS
XSD_NS = XSD
