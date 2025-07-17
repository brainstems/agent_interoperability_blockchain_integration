import json
from datetime import datetime
import logging
from typing import Any, Dict, List, Union, Tuple

from langchain_core.tools import BaseTool
# Removed PydanticV1BaseModel, PydanticV1Field, and Type as they are no longer needed for this simplified version
from langchain_core.agents import AgentAction, AgentFinish # Correct imports

logger = logging.getLogger(__name__)
# Ensure logging is configured, e.g., in the main script or by the application
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# This store will be populated by the crew_step_logger_callback
_observed_events_store: Dict[str, List[Dict[str, Any]]] = {}

def crew_step_logger_callback(
    step_output: Union[AgentFinish, List[Tuple[AgentAction, str]]], # Corrected type hint
    crew_run_id: str,
    task_description: str,
    agent_role: str
):
    """
    Callback function to log agent steps during a crew execution.
    This function is intended to be partially applied with crew_run_id, task_description, and agent_role.
    """
    current_time = datetime.utcnow().isoformat()
    processed_events: List[Dict[str, Any]] = []

    if isinstance(step_output, AgentFinish):
        event_data = {
            "type": "AgentFinish",
            "agent_role": agent_role,
            "return_values": step_output.return_values, # Direct attribute access
            "log": step_output.log, # Direct attribute access
            "timestamp": current_time,
            "crew_run_id": crew_run_id,
            "task_description": task_description,
        }
        processed_events.append(event_data)
        logger.info(f"[Callback] AgentFinish for {crew_run_id} by {agent_role}: {step_output.return_values}")
    elif isinstance(step_output, list):
        for item in step_output:
            if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], AgentAction):
                action, observation = item
                event_data = {
                    "type": "AgentAction",
                    "agent_role": agent_role,
                    "tool": action.tool, # Direct attribute access
                    "tool_input": str(action.tool_input),  # Convert tool_input to string for safety
                    "log": action.log, # Direct attribute access
                    "observation": observation,
                    "timestamp": current_time,
                    "crew_run_id": crew_run_id,
                    "task_description": task_description,
                }
                processed_events.append(event_data)
                logger.info(f"[Callback] AgentAction for {crew_run_id} by {agent_role}: Tool: {action.tool}, Input: {str(action.tool_input)}")
            else:
                logger.warning(f"[Callback] Unexpected item structure in step_output list for {crew_run_id} by {agent_role}: {item}")
                processed_events.append({
                    "type": "UnknownStepFormatInList",
                    "agent_role": agent_role,
                    "raw_item": str(item),
                    "timestamp": current_time,
                    "crew_run_id": crew_run_id,
                    "task_description": task_description,
                })
    else:
        logger.warning(f"[Callback] Unexpected step_output type for {crew_run_id} by {agent_role}: {type(step_output)}")
        processed_events.append({
            "type": "UnknownStepFormat",
            "agent_role": agent_role,
            "raw_output": str(step_output),
            "timestamp": current_time,
            "crew_run_id": crew_run_id,
            "task_description": task_description,
        })

    if crew_run_id not in _observed_events_store:
        _observed_events_store[crew_run_id] = []
    _observed_events_store[crew_run_id].extend(processed_events)

class FCEventSubscriberTool(BaseTool):
    name: str = "Functional Crew Event Retriever (Simplified)"
    description: str = (
        "Retrieves operational step data from Functional Crew runs. (Simplified for debugging) "
        "If 'crew_run_id' is provided in the input, it fetches events for that specific run. "
        "Otherwise, it lists available run IDs."
    )
    # args_schema and specific input class removed for simplification

    def _run(self, **kwargs: Any) -> str:
        """Retrieves stored events. Simplified for debugging."""
        logger.info(f"FCEventSubscriberTool called (simplified version) with kwargs: {kwargs}")
        
        crew_run_id_from_kwargs = kwargs.get('crew_run_id')
        
        if crew_run_id_from_kwargs:
            if crew_run_id_from_kwargs in _observed_events_store:
                events = _observed_events_store[crew_run_id_from_kwargs]
                logger.info(f"Retrieved {len(events)} events for crew_run_id '{crew_run_id_from_kwargs}' (from kwargs).")
                try:
                    return json.dumps(events, indent=2)
                except TypeError as e:
                    logger.error(f"Error serializing events for {crew_run_id_from_kwargs}: {e}")
                    return json.dumps({"error": f"Could not serialize events for {crew_run_id_from_kwargs}", "events_preview": str(events)[:500]})
            else:
                logger.info(f"No events found for crew_run_id '{crew_run_id_from_kwargs}' (from kwargs).")
                return json.dumps({"message": f"No events found for crew_run_id '{crew_run_id_from_kwargs}'.", "crew_run_id": crew_run_id_from_kwargs, "events": []})
        else:
            logger.info("FCEventSubscriberTool (simplified): No 'crew_run_id' provided in kwargs. Listing available run IDs.")
            return json.dumps({
                "message": "FCEventSubscriberTool (simplified) executed. Provide 'crew_run_id' in tool input for specific events.", 
                "available_run_ids_in_store": list(_observed_events_store.keys())
            })

    # _arun removed for simplification during this debugging phase
    # async def _arun(self, **kwargs: Any) -> str:
    #     """Async version of retrieving stored events. Simplified for debugging."""
    #     logger.info(f"FCEventSubscriberTool (async, simplified) called with kwargs: {kwargs}")
    #     # For simplicity, just call the synchronous version directly
    #     # In a real async tool, you'd use async I/O operations here
    #     return self._run(**kwargs)
