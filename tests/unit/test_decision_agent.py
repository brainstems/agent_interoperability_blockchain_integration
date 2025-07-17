"""
Tests for the DecisionAgent class.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any

from tests.unit.test_base import BaseInfrastructureTest
from agents.infrastructure_crew.infrastructure.agents.decision_agent import DecisionAgent

class TestDecisionAgent(BaseInfrastructureTest):
    """
    Tests for the DecisionAgent class.
    """
    
    @pytest_asyncio.fixture
    async def decision_agent(self):
        """Fixture that provides a configured DecisionAgent instance."""
        config = {
            "decision_strategy": "first_match",
            "rules": [
                {
                    "name": "test_rule_1",
                    "condition": "input.value > 50",
                    "action": "approve"
                },
                {
                    "name": "test_rule_2",
                    "condition": "input.value <= 50",
                    "action": "reject"
                }
            ]
        }
        agent = DecisionAgent(config)
        await agent._initialize()
        yield agent
        
    def test_agent_initialization(self, decision_agent):
        """
        Test DecisionAgent initialization.
        """
        assert decision_agent.name == "DecisionAgent"
        assert decision_agent.description == "Makes decisions based on input data and configured rules"
        assert decision_agent.decision_strategy == "first_match"
        assert len(decision_agent.rules) == 2
        
    async def test_decision_making(self, decision_agent):
        """
        Test decision making with different inputs.
        """
        # Test with value > 50
        request_high = {"input": {"value": 75}}
        response_high = await decision_agent.process(request_high)
        assert response_high["decision"] == "approve"
        assert response_high["rule"] == "test_rule_1"
        
        # Test with value <= 50
        request_low = {"input": {"value": 25}}
        response_low = await decision_agent.process(request_low)
        assert response_low["decision"] == "reject"
        assert response_low["rule"] == "test_rule_2"
        
    async def test_rule_evaluation(self, decision_agent):
        """
        Test rule evaluation with complex conditions.
        """
        # Add a rule with multiple conditions
        complex_rule = {
            "name": "complex_rule",
            "condition": "input.value > 50 AND input.type == 'priority'",
            "action": "priority_approve"
        }
        decision_agent.rules.append(complex_rule)
        
        # Test with matching conditions
        request_match = {"input": {"value": 75, "type": "priority"}}
        response_match = await decision_agent.process(request_match)
        assert response_match["decision"] == "priority_approve"
        assert response_match["rule"] == "complex_rule"
        
        # Test with partial match
        request_partial = {"input": {"value": 75, "type": "normal"}}
        response_partial = await decision_agent.process(request_partial)
        assert response_partial["decision"] == "approve"
        assert response_partial["rule"] == "test_rule_1"
        
    async def test_strategy_handling(self, decision_agent):
        """
        Test different decision strategies.
        """
        # Change strategy to all_matches
        decision_agent.decision_strategy = "all_matches"
        
        # Test with multiple matching rules
        request_multi = {"input": {"value": 75}}
        response_multi = await decision_agent.process(request_multi)
        assert len(response_multi["decisions"]) == 1  # Only first rule matches
        assert response_multi["decisions"][0]["decision"] == "approve"
        
    async def test_error_handling(self, decision_agent):
        """
        Test error handling with invalid inputs.
        """
        # Test with invalid input
        request_invalid = {"input": "not_a_dict"}
        response_invalid = await decision_agent.process(request_invalid)
        assert "error" in response_invalid
        assert "Invalid input format" in response_invalid["error"]
        
        # Test with invalid rule condition
        invalid_rule = {
            "name": "invalid_rule",
            "condition": "invalid syntax here",
            "action": "fail"
        }
        decision_agent.rules.append(invalid_rule)
        response_error = await decision_agent.process({"input": {"value": 100}})
        assert "error" in response_error
        assert "Invalid rule condition" in response_error["error"]
