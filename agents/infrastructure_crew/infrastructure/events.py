"""
Event Definitions

This module provides base event classes and enums used across the infrastructure.
"""

from typing import Dict, Any
from enum import Enum
import time
import uuid

class EventPriority(Enum):
    """Enumeration of event priorities."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

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
