"""
Rules Agent Implementation

This module provides the RulesAgent class which is responsible for evaluating
and applying business rules to input data.
"""

import asyncio
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable

from .base_agent import InfrastructureBaseAgent

# Type definitions for better type hints
RulesRequest = Dict[str, Any]
RulesResponse = Dict[str, Any]
Rule = Dict[str, Any]
RuleEvaluator = Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[bool]]

class RulesAgent(InfrastructureBaseAgent[RulesRequest, RulesResponse]):
    """
    An agent responsible for evaluating and applying business rules.
    
    The RulesAgent evaluates input data against a set of business rules and
    returns the results of the evaluation. It supports different types of rules
    and evaluation strategies.
    """
    
    name = "RulesAgent"
    description = "Evaluates and applies business rules to input data"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the RulesAgent.
        
        Args:
            config: Configuration dictionary for the agent
        """
        super().__init__(config or {})
        self.rules: List[Rule] = []
        self.rule_evaluators: Dict[str, RuleEvaluator] = {}
        self.default_evaluator = self._evaluate_simple_rule
    
    async def _initialize(self) -> None:
        """Initialize the rules agent and load rules."""
        self.logger.info("Initializing RulesAgent")
        await self._load_rules()
        self._register_default_evaluators()
    
    async def _load_rules(self) -> None:
        """Load rules from the configured source."""
        # In a real implementation, this would load rules from a file, database, etc.
        self.rules = self.config.get("rules", [])
        self.logger.info(f"Loaded {len(self.rules)} rules")
    
    def _register_default_evaluators(self) -> None:
        """Register default rule evaluators."""
        self.register_evaluator("simple", self._evaluate_simple_rule)
        self.register_evaluator("expression", self._evaluate_expression_rule)
    
    def register_evaluator(self, rule_type: str, evaluator: RuleEvaluator) -> None:
        """
        Register a custom rule evaluator.
        
        Args:
            rule_type: The type of rule the evaluator handles
            evaluator: A function that evaluates the rule
        """
        self.rule_evaluators[rule_type] = evaluator
    
    async def _process(self, request: RulesRequest) -> RulesResponse:
        """
        Process a rules evaluation request.
        
        Args:
            request: The rules evaluation request
            
        Returns:
            A dictionary containing the evaluation results
        """
        self.logger.debug(f"Processing rules evaluation request: {request}")
        
        # Get the rules to evaluate (default to all rules if none specified)
        rule_ids = request.get("rule_ids")
        rules_to_evaluate = self._get_rules_to_evaluate(rule_ids)
        
        # Evaluate each rule
        results = []
        for rule in rules_to_evaluate:
            result = await self._evaluate_rule(rule, request["data"])
            results.append({
                "rule_id": rule.get("id"),
                "rule_name": rule.get("name"),
                "passed": result,
                "message": rule.get("message", "")
            })
        
        # Prepare the response
        response = {
            "evaluation_id": request.get("evaluation_id"),
            "timestamp": asyncio.get_event_loop().time(),
            "results": results,
            "summary": self._generate_summary(results)
        }
        
        self.logger.info(f"Rules evaluation completed: {response['summary']}")
        return response
    
    def _get_rules_to_evaluate(self, rule_ids: Optional[List[str]] = None) -> List[Rule]:
        """
        Get the rules to evaluate based on the provided rule IDs.
        
        Args:
            rule_ids: Optional list of rule IDs to evaluate
            
        Returns:
            List of rules to evaluate
        """
        if not rule_ids:
            return self.rules
        
        return [rule for rule in self.rules if rule.get("id") in rule_ids]
    
    async def _evaluate_rule(self, rule: Rule, data: Dict[str, Any]) -> bool:
        """
        Evaluate a single rule against the input data.
        
        Args:
            rule: The rule to evaluate
            data: The input data
            
        Returns:
            True if the rule passes, False otherwise
        """
        rule_type = rule.get("type", "simple")
        evaluator = self.rule_evaluators.get(rule_type, self.default_evaluator)
        
        try:
            return await evaluator(rule, data)
        except Exception as e:
            self.logger.error(f"Error evaluating rule {rule.get('id')}: {e}", exc_info=True)
            return False
    
    async def _evaluate_simple_rule(self, rule: Rule, data: Dict[str, Any]) -> bool:
        """
        Evaluate a simple rule with field and value comparison.
        
        Args:
            rule: The rule to evaluate
            data: The input data
            
        Returns:
            True if the rule passes, False otherwise
        """
        field = rule.get("field")
        operator = rule.get("operator", "eq")
        value = rule.get("value")
        
        if field not in data:
            return False
        
        field_value = data[field]
        
        # Simple comparison logic
        if operator == "eq":
            return field_value == value
        elif operator == "ne":
            return field_value != value
        elif operator == "gt":
            return field_value > value
        elif operator == "lt":
            return field_value < value
        elif operator == "ge":
            return field_value >= value
        elif operator == "le":
            return field_value <= value
        elif operator == "in":
            return field_value in value
        elif operator == "contains":
            return value in field_value
        else:
            self.logger.warning(f"Unsupported operator: {operator}")
            return False
    
    async def _evaluate_expression_rule(self, rule: Rule, data: Dict[str, Any]) -> bool:
        """
        Evaluate a rule using a Python expression.
        
        Args:
            rule: The rule to evaluate
            data: The input data
            
        Returns:
            True if the rule passes, False otherwise
        """
        expression = rule.get("expression")
        if not expression:
            return False
        
        try:
            # In a real implementation, this would use a safe evaluation context
            # to prevent arbitrary code execution
            return bool(eval(expression, {"data": data}))
        except Exception as e:
            self.logger.error(f"Error evaluating expression: {e}")
            return False
    
    def _generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Generate a summary of the evaluation results.
        
        Args:
            results: List of evaluation results
            
        Returns:
            A dictionary with summary statistics
        """
        passed = sum(1 for r in results if r["passed"])
        total = len(results)
        
        return {
            "total_rules": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total > 0 else 0.0
        }
    
    async def _shutdown(self) -> None:
        """Clean up resources used by the agent."""
        self.logger.info("Shutting down RulesAgent")
