"""
Complex Event Processing (CEP) Agent

This module provides the CEPAgent class which handles event pattern matching and correlation.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Type, TypeVar, Generic, Union
from dataclasses import dataclass
from enum import Enum

from .base_agent import InfrastructureBaseAgent
from ...infrastructure.events import Event, EventPriority

T = TypeVar('T')

class PatternType(Enum):
    """Enumeration of pattern types."""
    SEQUENCE = "sequence"
    AND = "and"
    OR = "or"
    NOT = "not"
    COUNT = "count"
    TIME_WINDOW = "time_window"

class PatternCondition:
    """Represents a condition in a pattern."""
    
    def __init__(self, 
                 field: str, 
                 operator: str, 
                 value: Any,
                 pattern_type: PatternType = PatternType.AND):
        self.field = field
        self.operator = operator
        self.value = value
        self.pattern_type = pattern_type
        
    def matches(self, event_data: Dict[str, Any]) -> bool:
        """
        Check if the condition matches the event data.
        
        Args:
            event_data: The event data to check
            
        Returns:
            True if the condition matches, False otherwise
        """
        try:
            event_value = event_data.get(self.field)
            if self.operator == "==":
                return event_value == self.value
            elif self.operator == "!=":
                return event_value != self.value
            elif self.operator == ">":
                return event_value > self.value
            elif self.operator == "<":
                return event_value < self.value
            elif self.operator == ">=":
                return event_value >= self.value
            elif self.operator == "<=":
                return event_value <= self.value
            elif self.operator == "in":
                return event_value in self.value
            elif self.operator == "not in":
                return event_value not in self.value
            return False
        except Exception:
            return False

class EventPattern:
    """Represents a pattern to match against events."""
    
    def __init__(self, 
                 name: str, 
                 conditions: List[PatternCondition],
                 pattern_type: PatternType = PatternType.AND,
                 time_window: Optional[int] = None,
                 count: Optional[int] = None):
        self.name = name
        self.conditions = conditions
        self.pattern_type = pattern_type
        self.time_window = time_window
        self.count = count
        self.matches = []
        self.last_match_time = 0
        
    def matches_event(self, event: Event) -> bool:
        """
        Check if the pattern matches the event.
        
        Args:
            event: The event to check
            
        Returns:
            True if the pattern matches, False otherwise
        """
        if self.time_window and \
           event.timestamp - self.last_match_time > self.time_window:
            self.matches.clear()
            
        match = all(condition.matches(event.data) 
                    for condition in self.conditions)
                    
        if match:
            self.matches.append(event)
            self.last_match_time = event.timestamp
            
        if self.count and len(self.matches) >= self.count:
            return True
            
        return match

class CEPAgent(InfrastructureBaseAgent[Event, Dict[str, Any]]):
    """
    Complex Event Processing Agent
    
    This agent handles event pattern matching and correlation.
    It can detect complex patterns across multiple events and
    generate new events based on pattern matches.
    """
    
    name = "CEPAgent"
    description = "Complex Event Processing Agent"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the CEPAgent.
        
        Args:
            config: Configuration dictionary for the agent
        """
        default_config = {
            "patterns": [],
            "window_size": 1000,  # Number of events to keep in memory
            "max_patterns": 100,  # Maximum number of patterns
            "event_timeout": 3600,  # Time-to-live for events
        }
        
        if config:
            default_config.update(config)
            
        super().__init__(default_config)
        
        self.patterns: Dict[str, EventPattern] = {}
        self.event_buffer: List[Event] = []
        self._initialize_patterns()
    
    def _initialize_patterns(self):
        """Initialize patterns from configuration."""
        for pattern_config in self.config.get("patterns", []):
            try:
                conditions = [
                    PatternCondition(
                        field=cond["field"],
                        operator=cond["operator"],
                        value=cond["value"],
                        pattern_type=PatternType(cond.get("type", "and"))
                    )
                    for cond in pattern_config.get("conditions", [])
                ]
                
                pattern = EventPattern(
                    name=pattern_config["name"],
                    conditions=conditions,
                    pattern_type=PatternType(pattern_config.get("type", "and")),
                    time_window=pattern_config.get("time_window"),
                    count=pattern_config.get("count")
                )
                
                self.patterns[pattern.name] = pattern
                
            except Exception as e:
                self.logger.error(f"Error initializing pattern: {e}", exc_info=True)
    
    async def _process(self, event: Event) -> Dict[str, Any]:
        """
        Process incoming events and detect patterns.
        
        Args:
            event: The event to process
            
        Returns:
            Dictionary containing pattern matches and correlation results
        """
        try:
            # Add event to buffer
            self.event_buffer.append(event)
            if len(self.event_buffer) > self.config["window_size"]:
                self.event_buffer.pop(0)
            
            # Check all patterns
            matches = []
            for pattern_name, pattern in self.patterns.items():
                if pattern.matches_event(event):
                    matches.append({
                        "pattern": pattern_name,
                        "matched_events": pattern.matches,
                        "timestamp": time.time(),
                        "correlation_id": event.correlation_id
                    })
            
            # Generate new events for pattern matches
            for match in matches:
                new_event = Event(
                    event_type=f"pattern.matched.{match['pattern']}",
                    data=match,
                    priority=EventPriority.HIGH
                )
                await self.distribute_event(new_event)
            
            return {
                "event": event,
                "matches": matches,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing event: {e}", exc_info=True)
            return {
                "error": str(e),
                "event": event
            }
    
    def can_handle_event(self, event: Event) -> bool:
        """
        Check if this agent can handle the given event.
        
        Args:
            event: The event to check
            
        Returns:
            True if the agent can handle the event, False otherwise
        """
        return True  # CEP agent can handle any event
    
    async def add_pattern(self, pattern: EventPattern) -> bool:
        """
        Add a new pattern to monitor.
        
        Args:
            pattern: The pattern to add
            
        Returns:
            True if the pattern was added, False if not
        """
        if len(self.patterns) >= self.config["max_patterns"]:
            return False
            
        self.patterns[pattern.name] = pattern
        return True
    
    async def remove_pattern(self, pattern_name: str) -> bool:
        """
        Remove a pattern from monitoring.
        
        Args:
            pattern_name: The name of the pattern to remove
            
        Returns:
            True if the pattern was removed, False if not found
        """
        if pattern_name in self.patterns:
            del self.patterns[pattern_name]
            return True
        return False
    
    async def get_patterns(self) -> List[Dict[str, Any]]:
        """
        Get all currently monitored patterns.
        
        Returns:
            List of pattern configurations
        """
        return [{
            "name": pattern.name,
            "conditions": [
                {
                    "field": cond.field,
                    "operator": cond.operator,
                    "value": cond.value
                }
                for cond in pattern.conditions
            ],
            "type": pattern.pattern_type.value,
            "time_window": pattern.time_window,
            "count": pattern.count
        } for pattern in self.patterns.values()]
