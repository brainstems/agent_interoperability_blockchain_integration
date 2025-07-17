import logging
from typing import Optional, Dict, Any, List, Union # Retained for helpers

from pydantic import Field # Retained for potential future use in Config

from ...common.base_agent import BaseAgent, AgentConfig
from ..schemas.knowledge_graph_schemas import (
    KGEntity, Project, Task, Product, MarketSignal, PerformanceMetric, Decision, Outcome, KGRelationship # Schemas remain for potential type hinting or future use
)

# RDFLib imports
from rdflib import Graph, URIRef, Literal
from rdflib.plugins.sparql import prepareQuery # For prepared queries

# Project-specific RDF constants
from ..rdf_constants import (
    PROJECT_NS, NAME, DESCRIPTION, STATUS, ORIGINAL_ID, DATA, ENTITY_TYPE_PROP,
    RDF_NS, RDFS_NS, XSD_NS, TYPE_PROJECT, TYPE_TASK, TYPE_AGENT, TYPE_AGENT_CREW # Add other types/properties as needed
)

logger = logging.getLogger(__name__)

class KnowledgeGraphQueryAgentConfig(AgentConfig):
    # No specific config needed if RDF graph is passed in constructor for basic in-memory use
    # Future configurations like persistent graph store path could go here.
    pass

class KnowledgeGraphQueryAgent(BaseAgent):
    def __init__(self, 
                 agent_id: str, 
                 rdf_graph: Graph, # Added RDF graph instance
                 config: Optional[KnowledgeGraphQueryAgentConfig] = None):
        super().__init__(agent_id, config or KnowledgeGraphQueryAgentConfig())
        self.config: KnowledgeGraphQueryAgentConfig = self.config # Type hint
        self.rdf_graph = rdf_graph # Store the graph instance
        self.initialized = False 

    async def _initialize(self) -> None:
        logger.info(f"[{self.agent_id}] KnowledgeGraphQueryAgent initializing.")
        # Future: if config allows for persistent graph, load/connect here.
        if not isinstance(self.rdf_graph, Graph):
            logger.error(f"[{self.agent_id}] RDF Graph not provided or invalid type. Cannot initialize.")
            self.initialized = False
            return
        self.initialized = True
        logger.info(f"[{self.agent_id}] KnowledgeGraphQueryAgent initialized with RDF graph.")

    async def _process(self, request: Any) -> Any:
        """Processes an incoming request. Placeholder implementation."""
        logger.info(f"[{self.agent_id}] _process called with request: {request}")
        # This agent's primary interface is through specific query methods (e.g., get_entity_by_id).
        # This _process method might handle a generic query format if designed, or remain unused.
        # For now, returning None or raising NotImplementedError if direct calls are preferred.
        logger.warning(f"[{self.agent_id}] _process received unhandled request type: {type(request)}")
        return None # Or raise NotImplementedError("_process not implemented for KnowledgeGraphQueryAgent")

    async def start(self):
        if not self.initialized:
            logger.warning(f"[{self.agent_id}] Agent not initialized. Call initialize() first.")
            await self.initialize()
        logger.info(f"[{self.agent_id}] KnowledgeGraphQueryAgent started.")

    async def stop(self):
        # if self.kg_driver:
        #     self.kg_driver.close()
        self.initialized = False
        logger.info(f"[{self.agent_id}] KnowledgeGraphQueryAgent stopped.")

    # --- Example Query Methods (Simulated) ---

    def _entity_uri(self, entity_id: str, entity_type_name: str) -> URIRef:
        """Helper to create a unique URI for an entity based on its original ID."""
        return PROJECT_NS[f"{entity_type_name.lower().replace('_', '-')}/{entity_id}"]

    def _parse_sparql_result_row(self, row: Any, var_names: List[str]) -> Dict[str, Any]:
        """Converts a SPARQL query result row (tuple of rdflib terms) to a dictionary."""
        result_dict = {}
        for i, var_name in enumerate(var_names):
            term = row[i]
            if isinstance(term, Literal):
                result_dict[var_name] = term.toPython()
            elif isinstance(term, URIRef):
                result_dict[var_name] = str(term)
            else:
                result_dict[var_name] = str(term)
        return result_dict

    async def get_entity_by_id(self, entity_id: str, entity_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        logger.info(f"[{self.agent_id}] Querying RDF graph: Get entity by ORIGINAL_ID='{entity_id}', Type='{entity_type or 'any'}'")
        
        # === BEGIN DEBUGGING BLOCK ===
        try:
            # Try to guess the entity type string used for URI generation if not provided.
            # This is imperfect as the actual type string used during ingestion for the URI might vary.
            # Common types are 'Agent', 'AgentCrew', 'Project'.
            # A more robust way would be to iterate common types if entity_type is None.
            type_for_uri_debug = entity_type if entity_type else "Agent" # Default guess for debug
            if not entity_type and "crew" in entity_id.lower(): type_for_uri_debug = "AgentCrew"
            if not entity_type and "project" in entity_id.lower(): type_for_uri_debug = "Project"
            
            debug_entity_uri = self._entity_uri(entity_id, type_for_uri_debug) 
            
            logger.debug(f"[{self.agent_id}] DEBUG: Attempting to find triples for guessed URI {debug_entity_uri} (based on input id='{entity_id}', type_for_uri_debug='{type_for_uri_debug}')")
            count_uri_triples = 0
            for s_uri_check, p_uri_check, o_uri_check in self.rdf_graph.triples((debug_entity_uri, None, None)):
                logger.debug(f"[{self.agent_id}] DEBUG URI CHECK: Found triple for guessed URI: ({s_uri_check.n3()}, {p_uri_check.n3()}, {o_uri_check.n3()})")
                count_uri_triples += 1
            if count_uri_triples == 0:
                logger.debug(f"[{self.agent_id}] DEBUG URI CHECK: No triples found for guessed subject URI {debug_entity_uri}")

            logger.debug(f"[{self.agent_id}] DEBUG: Checking for predicate <{ORIGINAL_ID}> with object {Literal(entity_id).n3()} globally in graph.")
            count_id_match = 0
            for s_id_check, p_id_check, o_id_check in self.rdf_graph.triples((None, ORIGINAL_ID, Literal(entity_id))):
                logger.debug(f"[{self.agent_id}] DEBUG ID CHECK: Found triple with matching ORIGINAL_ID: ({s_id_check.n3()}, {p_id_check.n3()}, {o_id_check.n3()}). Subject URI: {s_id_check}")
                count_id_match +=1
            if count_id_match == 0:
                logger.debug(f"[{self.agent_id}] DEBUG ID CHECK: No triples found with predicate <{ORIGINAL_ID}> and object {Literal(entity_id).n3()} anywhere in the graph.")
            else:
                logger.debug(f"[{self.agent_id}] DEBUG ID CHECK: Found {count_id_match} triple(s) with matching ORIGINAL_ID globally.")

        except Exception as e_debug:
            logger.error(f"[{self.agent_id}] DEBUGGING BLOCK EXCEPTION: {e_debug}", exc_info=True)
        # === END DEBUGGING BLOCK ===

        original_id_predicate_uri = str(ORIGINAL_ID)

        # Step 1: ASK query to check for existence
        ask_query_str = f"""
            ASK WHERE {{
                ?s <{original_id_predicate_uri}> {Literal(entity_id).n3()} .
            }}
        """
        logger.debug(f"[{self.agent_id}] Executing ASK SPARQL query for ORIGINAL_ID='{entity_id}':\n{ask_query_str}")
        
        try:
            ask_qres = self.rdf_graph.query(ask_query_str)
            entity_exists = bool(list(ask_qres)[0])
            logger.debug(f"[{self.agent_id}] ASK Query for ORIGINAL_ID='{entity_id}' returned: {entity_exists}")

            if not entity_exists:
                logger.debug(f"[{self.agent_id}] Entity with ORIGINAL_ID='{entity_id}' not found by ASK query.")
                return None

            # Step 2: If entity exists, fetch all its properties with the original SELECT query
            select_query_str = f"""
                SELECT ?s ?p ?o
                WHERE {{
                    ?s ?p ?o ;
                       <{original_id_predicate_uri}> {Literal(entity_id).n3()} .
                    OPTIONAL {{ ?s <{RDF_NS.type}> ?type_uri . }}
                }}
            """
            logger.debug(f"[{self.agent_id}] Entity exists (ASK=true). Executing SELECT SPARQL query for ORIGINAL_ID='{entity_id}':\n{select_query_str}")
            
            select_qres = self.rdf_graph.query(select_query_str)
            results_list = list(select_qres)
            logger.debug(f"[{self.agent_id}] SELECT Query for ORIGINAL_ID='{entity_id}' returned {len(results_list)} triple components.")

            if not results_list:
                # This case should ideally not happen if ASK was true, but good to log
                logger.error(f"[{self.agent_id}] CONTRADICTION: ASK for ORIGINAL_ID='{entity_id}' was true, but SELECT query returned no results.")
                return None

            entity_props = {}
            entity_uri = None
            for row_tuple in results_list:
                s, p, o = row_tuple
                if entity_uri is None:
                    entity_uri = str(s)
                
                prop_name = str(p)
                if prop_name.startswith(str(PROJECT_NS)):
                    prop_key = prop_name[len(str(PROJECT_NS)):]
                elif prop_name.startswith(str(RDF_NS)):
                    prop_key = f"rdf_{prop_name[len(str(RDF_NS)):]}"
                else:
                    prop_key = prop_name

                value = o.toPython() if isinstance(o, Literal) else str(o)
                
                if prop_key in entity_props:
                    if not isinstance(entity_props[prop_key], list):
                        entity_props[prop_key] = [entity_props[prop_key]]
                    entity_props[prop_key].append(value)
                else:
                    entity_props[prop_key] = value
            
            if entity_uri:
                entity_props['uri'] = entity_uri
                original_id_key = str(ORIGINAL_ID).split('/')[-1] # Use the simplified key
                if original_id_key not in entity_props:
                     entity_props[original_id_key] = entity_id # Ensure original ID is in the dict
                return entity_props
            else:
                # Should be unreachable if results_list is not empty
                logger.error(f"[{self.agent_id}] Logic error: entity_uri is None but results_list was not empty for ORIGINAL_ID='{entity_id}'.")
                return None

        except Exception as e:
            logger.error(f"[{self.agent_id}] Error executing SPARQL query in get_entity_by_id for ORIGINAL_ID='{entity_id}': {e}", exc_info=True)
            return None

    async def find_entities(self, entity_type: str, properties: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        logger.info(f"[{self.agent_id}] Querying RDF graph: Find entities of Type='{entity_type}' with properties={properties}, limit={limit}")

        rdf_type = None
        if isinstance(entity_type, URIRef):
            rdf_type = entity_type
        elif isinstance(entity_type, str):
            # Try to see if it's a key in our map first
            type_uri_map = {
                "Project": TYPE_PROJECT,
                "Task": TYPE_TASK,
                "Agent": TYPE_AGENT, 
                "AgentCrew": TYPE_AGENT_CREW, 
                # Add other entity types from rdf_constants as needed
                # "Product": TYPE_PRODUCT, ...
            }
            rdf_type = type_uri_map.get(entity_type)
            
            if not rdf_type:
                # If not in map, assume it might be a string URI
                try:
                    # Attempt to treat as a URI if not found in the map
                    rdf_type = URIRef(entity_type) 
                    logger.info(f"[{self.agent_id}] Interpreting entity_type '{entity_type}' as a direct URI.")
                except Exception: # Broad exception if it's not a valid URI string
                    logger.error(f"[{self.agent_id}] Could not interpret entity_type '{entity_type}' as a known type or URI.")
                    return []
        
        if not rdf_type: # Safeguard
            logger.error(f"[{self.agent_id}] Unknown or invalid entity type: {entity_type} for find_entities")
            return []

        prop_uri_map = {
            "name": NAME,
            "status": STATUS,
            "description": DESCRIPTION,
            "originalId": ORIGINAL_ID,
            # Add other properties from rdf_constants
        }

        filter_clauses = [f"  ?s <{RDF_NS.type}> <{rdf_type}> ."]
        for prop_key, prop_value in properties.items():
            prop_uri = None
            if isinstance(prop_key, URIRef):
                prop_uri = prop_key # If key is already a URIRef, use it directly
            elif isinstance(prop_key, str):
                prop_uri = prop_uri_map.get(prop_key) # Try mapping from short name
        
            if prop_uri:
                filter_clauses.append(f"  ?s <{prop_uri}> {Literal(prop_value).n3()} .")
            else:
                logger.warning(f"[{self.agent_id}] Unknown property key or unmappable string: {prop_key} in find_entities. Skipping filter.")
        
        filters_str = "\n".join(filter_clauses)

        query_str = f"""
            SELECT ?s ?p ?o
            WHERE {{
              {{
                SELECT DISTINCT ?s
                WHERE {{
{filters_str}
                }}
                LIMIT {limit}
              }}
              ?s ?p ?o .
            }}
        """

        entities_map: Dict[str, Dict[str, Any]] = {}
        try:
            qres = self.rdf_graph.query(query_str)
            for row_tuple in qres:
                s_uri, p_uri, o_term = row_tuple
                s_str = str(s_uri)

                if s_str not in entities_map:
                    entities_map[s_str] = {'uri': s_str} # Initialize with URI
                
                prop_name = str(p_uri)
                # Simplify property name for the dictionary key
                if prop_name.startswith(str(PROJECT_NS)):
                    dict_key = prop_name[len(str(PROJECT_NS)):]
                elif prop_name.startswith(str(RDF_NS)):
                    dict_key = f"rdf_{prop_name[len(str(RDF_NS)):]}"
                elif prop_name.startswith(str(RDFS_NS)):
                    dict_key = f"rdfs_{prop_name[len(str(RDFS_NS)):]}"
                else:
                    # For unknown namespaces, use the full URI or a simplified version
                    dict_key = prop_name.split('/')[-1] if '#' not in prop_name else prop_name.split('#')[-1]

                value = o_term.toPython() if isinstance(o_term, Literal) else str(o_term)

                if dict_key in entities_map[s_str]:
                    current_val = entities_map[s_str][dict_key]
                    if not isinstance(current_val, list):
                        entities_map[s_str][dict_key] = [current_val]
                    entities_map[s_str][dict_key].append(value)
                else:
                    entities_map[s_str][dict_key] = value
            
            return list(entities_map.values())
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error executing SPARQL query in find_entities: {e}", exc_info=True)
            return []

    async def get_related_entities(self, source_entity_id: str, relationship_type: Optional[str] = None, target_entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        log_msg = f"[{self.agent_id}] Querying RDF graph: Get entities related to ORIGINAL_ID='{source_entity_id}'"
        if relationship_type: log_msg += f" via relationship '{relationship_type}'"
        if target_entity_type: log_msg += f" of type '{target_entity_type}'"
        logger.info(log_msg)

        # Assumes rdf_constants.py defines relationship constants like HAS_MEMBER, DEPENDS_ON etc.
        # Example: from ..rdf_constants import HAS_MEMBER, DEPENDS_ON, TYPE_PROJECT, TYPE_TASK
        # For now, we'll use a local map or expect full URIs if not in rdf_constants
        rel_uri_map = {
            # "HAS_MEMBER": HAS_MEMBER, # Example from rdf_constants
            # "DEPENDS_ON": DEPENDS_ON,
        }
        type_uri_map = {
            "Project": TYPE_PROJECT,
            "Task": TYPE_TASK,
            # Add other entity types
        }

        target_type_filter_str = ""
        if target_entity_type:
            target_rdf_type = type_uri_map.get(target_entity_type)
            if target_rdf_type:
                target_type_filter_str = f"  ?target_uri <{RDF_NS.type}> <{target_rdf_type}> ."
            else:
                logger.warning(f"[{self.agent_id}] Unknown target entity type: {target_entity_type}. No type filter applied.")

        relationship_pattern_parts = []
        source_entity_id_literal = Literal(source_entity_id).n3()

        if relationship_type:
            rel_uri = rel_uri_map.get(relationship_type) # Or expect relationship_type to be a full URI string
            if not rel_uri:
                # Fallback: assume relationship_type might be a full URI string or a known short name from PROJECT_NS
                try: 
                    rel_uri = URIRef(relationship_type) if ':' in relationship_type else PROJECT_NS[relationship_type]
                except Exception:
                    logger.error(f"[{self.agent_id}] Invalid relationship type: {relationship_type}. Cannot form query.")
                    return []
            relationship_pattern_parts.append(f"    ?source_uri <{rel_uri}> ?target_uri .")
        else:
            # Find any relationship (outgoing and incoming)
            relationship_pattern_parts.append(
                f"""  {{
    ?source_uri ?any_rel_outgoing ?target_uri .
    FILTER(?target_uri != ?source_uri)
  }} UNION {{
    ?target_uri ?any_rel_incoming ?source_uri .
    FILTER(?target_uri != ?source_uri)
  }}"""
            )
        
        relationship_patterns = "\n".join(relationship_pattern_parts)

        # Subquery to find distinct target URIs, then fetch all their properties
        query_str = f"""
            SELECT ?target_uri ?p ?o
            WHERE {{
              {{
                SELECT DISTINCT ?target_uri
                WHERE {{
                  ?source_uri <{ORIGINAL_ID}> {source_entity_id_literal} .
{relationship_patterns}
{target_type_filter_str}
                }}
              }}
              ?target_uri ?p ?o .
            }}
        """

        entities_map: Dict[str, Dict[str, Any]] = {}
        try:
            qres = self.rdf_graph.query(query_str)
            for row_tuple in qres:
                target_s_uri, p_uri, o_term = row_tuple
                target_s_str = str(target_s_uri)

                if target_s_str not in entities_map:
                    entities_map[target_s_str] = {'uri': target_s_str}
                
                prop_name = str(p_uri)
                if prop_name.startswith(str(PROJECT_NS)):
                    dict_key = prop_name[len(str(PROJECT_NS)):]
                elif prop_name.startswith(str(RDF_NS)):
                    dict_key = f"rdf_{prop_name[len(str(RDF_NS)):]}"
                elif prop_name.startswith(str(RDFS_NS)):
                    dict_key = f"rdfs_{prop_name[len(str(RDFS_NS)):]}"
                else:
                    dict_key = prop_name.split('/')[-1] if '#' not in prop_name else prop_name.split('#')[-1]

                value = o_term.toPython() if isinstance(o_term, Literal) else str(o_term)

                if dict_key in entities_map[target_s_str]:
                    current_val = entities_map[target_s_str][dict_key]
                    if not isinstance(current_val, list):
                        entities_map[target_s_str][dict_key] = [current_val]
                    entities_map[target_s_str][dict_key].append(value)
                else:
                    entities_map[target_s_str][dict_key] = value
            
            return list(entities_map.values())
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error executing SPARQL query in get_related_entities: {e}", exc_info=True)
            return []

    async def execute_raw_query(self, query_language: str, query_string: str) -> List[Dict[str, Any]]:
        logger.info(f"[{self.agent_id}] Executing raw query ({query_language}):\n{query_string}")

        if query_language.upper() != "SPARQL":
            logger.error(f"[{self.agent_id}] Unsupported query language: {query_language}. Only SPARQL is supported.")
            return []

        try:
            qres = self.rdf_graph.query(query_string)
            results = []

            # qres.type can be 'SELECT', 'ASK', 'CONSTRUCT', 'DESCRIBE'
            if qres.type == 'SELECT':
                # For SELECT, qres.vars gives the variable names (rdflib.term.Variable objects)
                var_names = [str(var) for var in qres.vars]
                for row_tuple in qres:
                    # row_tuple is a tuple of rdflib terms (Literal, URIRef, BNode)
                    row_dict = {}
                    for i, term in enumerate(row_tuple):
                        var_name = var_names[i]
                        if isinstance(term, Literal):
                            row_dict[var_name] = term.toPython()
                        elif isinstance(term, URIRef):
                            row_dict[var_name] = str(term)
                        elif isinstance(term, BNode):
                            row_dict[var_name] = str(term) # Represent BNode as string
                        else:
                            row_dict[var_name] = str(term) # Fallback
                    results.append(row_dict)
            elif qres.type == 'ASK':
                # For ASK, qres.askAnswer is a boolean
                results.append({"boolean_result": qres.askAnswer})
            elif qres.type == 'CONSTRUCT' or qres.type == 'DESCRIBE':
                # These return a new Graph. We can serialize it or convert to triples.
                # For simplicity, let's return a message or serialize to N-Triples.
                graph_data = qres.serialize(format='nt') # N-Triples format
                results.append({"graph_serialization_nt": graph_data})
                logger.info(f"[{self.agent_id}] CONSTRUCT/DESCRIBE query returned a graph. Serialized to N-Triples.")
            else:
                logger.warning(f"[{self.agent_id}] Unknown SPARQL query result type: {qres.type}")
                results.append({"message": f"Query executed, but result type '{qres.type}' handling not fully implemented for direct dict conversion."})
            
            return results
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error executing raw SPARQL query: {e}\nQuery:\n{query_string}", exc_info=True)
            return []

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "initialized": self.initialized,
            "config": self.config.dict(),
            "mode": "RDFLib_Graph_Direct_Query",
            "graph_size": len(self.rdf_graph) if self.rdf_graph else 0
        }
