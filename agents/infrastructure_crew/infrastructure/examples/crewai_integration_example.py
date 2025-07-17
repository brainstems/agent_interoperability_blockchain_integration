"""
Example of integrating infrastructure agents with CrewAI.

This example shows how to use our infrastructure agents with the CrewAI framework.
"""

import asyncio
from typing import Dict, Any, Optional

from crewai import Crew, Process

from infrastructure.agents import DecisionAgent, RulesAgent, AmbiguityAgent, StateAgent
from infrastructure.crewai import CrewAIAgentAdapter, InfrastructureTask, create_csv_search_tool

# Example configuration for our agents
AGENT_CONFIG = {
    "decision_agent": {
        "decision_engine": {
            "timeout_seconds": 30,
            "max_retries": 3
        }
    },
    "rules_agent": {
        "rules_engine": {
            "strict_mode": True
        },
        "rules": {
            "rules_file": "path/to/rules.yaml"
        }
    },
    "ambiguity_agent": {
        "ambiguity_threshold": 0.7,
        "llm": {
            "model": "gpt-4"
        }
    },
    "state_agent": {
        "state_manager": {
            "redis_url": "redis://localhost:6379/0",
            "default_ttl": 3600
        }
    }
}

# Example data models
class DecisionRequest:
    def __init__(self, event: Dict, context: Optional[Dict] = None):
        self.event = event
        self.context = context or {}

class DecisionResponse:
    def __init__(self, decision: Dict, confidence: float):
        self.decision = decision
        self.confidence = confidence

async def main():
    """Run the crewAI integration example."""
    # Create our infrastructure agents
    decision_agent = DecisionAgent(config=AGENT_CONFIG["decision_agent"])
    rules_agent = RulesAgent(config=AGENT_CONFIG["rules_agent"])
    ambiguity_agent = AmbiguityAgent(config=AGENT_CONFIG["ambiguity_agent"])
    state_agent = StateAgent(config=AGENT_CONFIG["state_agent"])
    
    # Create a CSV search tool
    csv_tool = create_csv_search_tool(
        csv_path="data/sales_data.csv",
        description="Search sales data for patterns and trends"
    )
    
    # Create crewAI-compatible tasks using our agents
    decision_task = InfrastructureTask(
        agent=decision_agent,
        description="Analyze the sales data and make decisions",
        expected_output="A list of decisions with confidence scores",
        tools=[csv_tool]  # Add tools the agent can use
    )
    
    rules_task = InfrastructureTask(
        agent=rules_agent,
        description="Evaluate business rules against the current state",
        expected_output="A list of matching rules and actions to take"
    )
    
    ambiguity_task = InfrastructureTask(
        agent=ambiguity_agent,
        description="Detect and resolve ambiguous situations in the data",
        expected_output="A list of detected ambiguities with resolution suggestions"
    )
    
    # Create a crew with our tasks
    crew = Crew(
        agents=[
            CrewAIAgentAdapter(decision_agent),
            CrewAIAgentAdapter(rules_agent),
            CrewAIAgentAdapter(ambiguity_agent),
            CrewAIAgentAdapter(state_agent)
        ],
        tasks=[decision_task, rules_task, ambiguity_task],
        process=Process.sequential,
        verbose=True
    )
    
    # Run the crew with some input data
    input_data = {
        "event": {
            "type": "sales_analysis",
            "data": {"region": "north_america", "timeframe": "Q1_2023"}
        },
        "context": {"priority": "high"}
    }
    
    print("Starting crew execution...")
    result = await crew.kickoff(inputs=input_data)
    print("\nCrew execution completed!")
    print("Results:", result)

if __name__ == "__main__":
    asyncio.run(main())
