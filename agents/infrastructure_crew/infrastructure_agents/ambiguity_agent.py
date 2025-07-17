"""
Ambiguity Agent Implementation

This module provides the AmbiguityAgent class which is responsible for detecting
and resolving ambiguities in input data and requests.
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union

from .base_agent import InfrastructureBaseAgent

# Type definitions for better type hints
AmbiguityRequest = Dict[str, Any]
AmbiguityResponse = Dict[str, Any]
AmbiguityResult = Dict[str, Any]

class AmbiguityAgent(InfrastructureBaseAgent[AmbiguityRequest, AmbiguityResponse]):
    """
    An agent responsible for detecting and resolving ambiguities.
    
    The AmbiguityAgent analyzes input data to identify potential ambiguities
    and provides suggestions for resolution. It can be used to improve the
    quality of user input and prevent misunderstandings.
    """
    
    name = "AmbiguityAgent"
    description = "Detects and resolves ambiguities in input data"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the AmbiguityAgent.
        
        Args:
            config: Configuration dictionary for the agent
        """
        default_config = {
            "detection_threshold": 0.7,
            "max_suggestions": 3,
            "enabled_detectors": ["missing_fields", "vague_terms", "contradictions"],
            "resolvers": {
                "default": "suggest_options"
            }
        }
        
        # Merge provided config with defaults
        if config:
            default_config.update(config)
            
        super().__init__(default_config)
        
        # Initialize detectors and resolvers
        self.detectors = {}
        self.resolvers = {}
        self._setup_detectors()
        self._setup_resolvers()
    
    async def _initialize(self) -> None:
        """Initialize the ambiguity agent."""
        self.logger.info("Initializing AmbiguityAgent")
        # Any additional initialization can go here
    
    def _setup_detectors(self) -> None:
        """Register all available ambiguity detectors."""
        self.detectors["missing_fields"] = self._detect_missing_fields
        self.detectors["vague_terms"] = self._detect_vague_terms
        self.detectors["contradictions"] = self._detect_contradictions
    
    def _setup_resolvers(self) -> None:
        """Register all available ambiguity resolvers."""
        self.resolvers["suggest_options"] = self._resolve_suggest_options
        self.resolvers["use_default"] = self._resolve_use_default
        self.resolvers["ask_clarification"] = self._resolve_ask_clarification
    
    async def _process(self, request: AmbiguityRequest) -> AmbiguityResponse:
        """
        Process an ambiguity detection request.
        
        Args:
            request: The ambiguity detection request
            
        Returns:
            A dictionary containing the detected ambiguities and suggestions
        """
        self.logger.debug(f"Processing ambiguity detection request: {request}")
        
        # Get the input data to analyze
        input_data = request.get("data", {})
        context = request.get("context", {})
        
        # Detect ambiguities
        detected_ambiguities = await self._detect_ambiguities(input_data, context)
        
        # Resolve ambiguities
        resolution_results = await self._resolve_ambiguities(detected_ambiguities, context)
        
        # Prepare the response
        response = {
            "request_id": request.get("request_id"),
            "timestamp": asyncio.get_event_loop().time(),
            "detected_ambiguities": detected_ambiguities,
            "resolutions": resolution_results,
            "summary": self._generate_summary(detected_ambiguities, resolution_results)
        }
        
        self.logger.info(f"Ambiguity detection completed: {response['summary']}")
        return response
    
    async def _detect_ambiguities(self, data: Dict[str, Any], context: Dict[str, Any]) -> List[AmbiguityResult]:
        """
        Detect ambiguities in the input data.
        
        Args:
            data: The input data to analyze
            context: Additional context for ambiguity detection
            
        Returns:
            A list of detected ambiguities
        """
        ambiguities = []
        
        # Run enabled detectors
        for detector_name in self.config["enabled_detectors"]:
            detector = self.detectors.get(detector_name)
            if detector:
                try:
                    detector_results = await detector(data, context)
                    if detector_results:
                        if isinstance(detector_results, list):
                            ambiguities.extend(detector_results)
                        else:
                            ambiguities.append(detector_results)
                except Exception as e:
                    self.logger.error(f"Error in detector '{detector_name}': {e}", exc_info=True)
        
        return ambiguities
    
    async def _resolve_ambiguities(
        self, 
        ambiguities: List[AmbiguityResult], 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Resolve detected ambiguities.
        
        Args:
            ambiguities: List of detected ambiguities
            context: Additional context for resolution
            
        Returns:
            A list of resolution results
        """
        resolutions = []
        
        for ambiguity in ambiguities:
            resolver_name = ambiguity.get("resolver", self.config["resolvers"].get("default"))
            resolver = self.resolvers.get(resolver_name)
            
            if resolver:
                try:
                    resolution = await resolver(ambiguity, context)
                    resolutions.append({
                        "ambiguity_id": ambiguity.get("id"),
                        "type": ambiguity.get("type"),
                        "resolver": resolver_name,
                        "resolution": resolution,
                        "confidence": ambiguity.get("confidence", 0.0)
                    })
                except Exception as e:
                    self.logger.error(f"Error in resolver '{resolver_name}': {e}", exc_info=True)
        
        return resolutions
    
    # Detector implementations
    async def _detect_missing_fields(
        self, 
        data: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> List[AmbiguityResult]:
        """Detect missing required fields in the input data."""
        required_fields = context.get("required_fields", [])
        missing_fields = [field for field in required_fields if field not in data]
        
        if not missing_fields:
            return []
        
        return [{
            "id": f"missing_field_{i}",
            "type": "missing_field",
            "field": field,
            "message": f"Required field '{field}' is missing",
            "confidence": 1.0,
            "resolver": "ask_clarification"
        } for i, field in enumerate(missing_fields)]
    
    async def _detect_vague_terms(
        self, 
        data: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> List[AmbiguityResult]:
        """Detect vague or ambiguous terms in the input data."""
        vague_terms = context.get("vague_terms", [
            "some", "many", "few", "soon", "later", "recently",
            "better", "worse", "good", "bad", "fast", "slow"
        ])
        
        detected = []
        
        for field, value in data.items():
            if not isinstance(value, str):
                continue
                
            words = value.lower().split()
            found_terms = [term for term in vague_terms if term in words]
            
            for term in found_terms:
                detected.append({
                    "id": f"vague_term_{len(detected)}",
                    "type": "vague_term",
                    "field": field,
                    "term": term,
                    "message": f"Vague term '{term}' detected in field '{field}'",
                    "confidence": 0.8,
                    "resolver": "suggest_options"
                })
        
        return detected
    
    async def _detect_contradictions(
        self, 
        data: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> List[AmbiguityResult]:
        """Detect contradictions in the input data."""
        # This is a simplified implementation
        # In a real system, this would use more sophisticated logic
        return []
    
    # Resolver implementations
    async def _resolve_suggest_options(
        self, 
        ambiguity: AmbiguityResult, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve ambiguity by suggesting options."""
        # In a real implementation, this would generate meaningful options
        # based on the ambiguity type and context
        return {
            "strategy": "suggest_options",
            "options": ["Option 1", "Option 2", "Option 3"],
            "message": "Please select one of the following options"
        }
    
    async def _resolve_use_default(
        self, 
        ambiguity: AmbiguityResult, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve ambiguity by using a default value."""
        return {
            "strategy": "use_default",
            "default_value": None,
            "message": "Using default value"
        }
    
    async def _resolve_ask_clarification(
        self, 
        ambiguity: AmbiguityResult, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve ambiguity by asking for clarification."""
        return {
            "strategy": "ask_clarification",
            "message": f"Please provide more information about: {ambiguity.get('message', 'this')}"
        }
    
    def _generate_summary(
        self, 
        ambiguities: List[AmbiguityResult], 
        resolutions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a summary of the ambiguity detection and resolution.
        
        Args:
            ambiguities: List of detected ambiguities
            resolutions: List of resolution results
            
        Returns:
            A dictionary with summary statistics
        """
        resolved = len([r for r in resolutions if r.get("resolution")])
        total = len(ambiguities)
        
        return {
            "total_ambiguities": total,
            "resolved": resolved,
            "unresolved": total - resolved,
            "resolution_rate": resolved / total if total > 0 else 1.0
        }
    
    async def _shutdown(self) -> None:
        """Clean up resources used by the agent."""
        self.logger.info("Shutting down AmbiguityAgent")
