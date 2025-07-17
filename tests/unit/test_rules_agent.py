"""
Tests for the RulesAgent class.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any, List, Callable, Awaitable

from tests.unit.test_base import BaseInfrastructureTest
from agents.infrastructure_crew.infrastructure.agents.rules_agent import RulesAgent, RuleEvaluator

class TestRulesAgent(BaseInfrastructureTest):
    """
    Tests for the RulesAgent class.
    """
    
    @pytest_asyncio.fixture
    async def rules_agent(self):
        """Fixture that provides a configured RulesAgent instance."""
        config = {
            "rules": [
                {
                    "name": "age_rule",
                    "type": "simple",
                    "condition": "input.age >= 18",
                    "action": "allow"
                },
                {
                    "name": "credit_rule",
                    "type": "complex",
                    "conditions": [
                        {"field": "credit_score", "operator": ">=", "value": 700},
                        {"field": "income", "operator": ">", "value": 50000}
                    ],
                    "action": "approve"
                }
            ]
        }
        agent = RulesAgent(config)
        await agent._initialize()
        yield agent
        
    def test_agent_initialization(self, rules_agent):
        """
        Test RulesAgent initialization.
        """
        assert rules_agent.name == "RulesAgent"
        assert rules_agent.description == "Evaluates and applies business rules to input data"
        assert len(rules_agent.rules) == 2
        assert len(rules_agent.rule_evaluators) > 0
        
    async def test_rule_evaluation(self, rules_agent):
        """
        Test rule evaluation with different inputs.
        """
        # Test simple rule
        request_age = {"age": 25}
        response_age = await rules_agent.process(request_age)
        assert response_age["result"] == "allow"
        assert response_age["matched_rules"] == ["age_rule"]
        
        # Test complex rule
        request_credit = {
            "credit_score": 750,
            "income": 60000
        }
        response_credit = await rules_agent.process(request_credit)
        assert response_credit["result"] == "approve"
        assert response_credit["matched_rules"] == ["credit_rule"]
        
    async def test_custom_evaluator(self, rules_agent):
        """
        Test custom rule evaluator.
        """
        # Register custom evaluator
        async def custom_evaluator(rule: Dict[str, Any], data: Dict[str, Any]) -> bool:
            return data.get("custom_flag", False)
            
        rules_agent.rule_evaluators["custom"] = custom_evaluator
        
        # Add custom rule
        custom_rule = {
            "name": "custom_rule",
            "type": "custom",
            "action": "accept"
        }
        rules_agent.rules.append(custom_rule)
        
        # Test with custom flag
        request_custom = {"custom_flag": True}
        response_custom = await rules_agent.process(request_custom)
        assert response_custom["result"] == "accept"
        assert response_custom["matched_rules"] == ["custom_rule"]
        
    async def test_rule_combination(self, rules_agent):
        """
        Test combination of multiple rules.
        """
        # Add another rule
        additional_rule = {
            "name": "income_rule",
            "type": "simple",
            "condition": "input.income > 30000",
            "action": "eligible"
        }
        rules_agent.rules.append(additional_rule)
        
        # Test with multiple matching rules
        request_combined = {
            "age": 30,
            "income": 60000
        }
        response_combined = await rules_agent.process(request_combined)
        assert "matched_rules" in response_combined
        assert len(response_combined["matched_rules"]) == 2
        assert "age_rule" in response_combined["matched_rules"]
        assert "income_rule" in response_combined["matched_rules"]
        
    async def test_error_handling(self, rules_agent):
        """
        Test error handling with invalid rules and inputs.
        """
        # Test invalid rule type
        invalid_rule = {
            "name": "invalid_rule",
            "type": "unknown_type",
            "action": "fail"
        }
        rules_agent.rules.append(invalid_rule)
        response_invalid = await rules_agent.process({"test": "data"})
        assert "error" in response_invalid
        assert "Unknown rule type" in response_invalid["error"]
        
        # Test invalid input
        request_invalid = [1, 2, 3]  # Invalid input format
        response_error = await rules_agent.process(request_invalid)
        assert "error" in response_error
        assert "Invalid input format" in response_error["error"]
