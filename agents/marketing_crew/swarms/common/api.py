from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
import requests

router = APIRouter()

# Base URL configuration
BASE_API_URL = "https://agent-blockchain-integration.zeljko.dev"
STATE_API_ENDPOINT = f"{BASE_API_URL}/api/state"
EVENT_API_ENDPOINT = f"{BASE_API_URL}/api/event"


async def store_agent_event(
    event_id: str,
    agent_id: str,
    event_data: Dict[Any, Any]
) -> Dict[str, Any]:
    """
    Store agent event information.
    
    Args:
        event_id: The ID of the event
        agent_id: The ID of the agent
        event_data: Dictionary containing event data
        
    Returns:
        Dict containing the stored event data
        
    Raises:
        HTTPException: If required fields are missing
    """
    # Prepare the request payload
    payload = {
        "eventId": event_id,
        "agentId": agent_id,
        "data": event_data
    }

    try:
        # Forward the request to the external API
        response = requests.post(EVENT_API_ENDPOINT, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store event: {str(e)}"
        )


async def store_agent_state(
    agent_id: str,
    state_data: Dict[Any, Any]
) -> Dict[str, Any]:
    """
    Store agent state information.
    
    Args:
        agent_id: The ID of the agent
        state_data: Dictionary containing agent state data
        
    Returns:
        Dict containing the stored state data
        
    Raises:
        HTTPException: If required fields are missing
    """
    # Validate agent_id
    if not agent_id:
        raise HTTPException(
            status_code=400,
            detail="Missing required field: agent_id is required"
        )
    
    # Add timestamp if not provided
    if "lastUpdated" not in state_data:
        state_data["lastUpdated"] = datetime.utcnow().isoformat()
    
    # Convert state_data to JSON-serializable format
    serializable_data = {}
    for key, value in state_data.items():
        if hasattr(value, '__dict__'):
            # Convert custom objects to dict
            serializable_data[key] = value.__dict__
        elif hasattr(value, 'to_dict'):
            # Use to_dict() method if available
            serializable_data[key] = value.to_dict()
        else:
            # Keep primitive types as is
            serializable_data[key] = value

    timestamp = datetime.utcnow().isoformat(timespec='microseconds')
    print(f"Posting state data to {STATE_API_ENDPOINT}/{agent_id}-{timestamp}:")
    print(f"Data: {serializable_data}")

    try:
        # Append timestamp to agent_id in the URL
        url = f"{STATE_API_ENDPOINT}/{agent_id}-{timestamp}"
        # Forward the request to the external API
        response = requests.post(url, json=serializable_data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store state: {str(e)}"
        )
