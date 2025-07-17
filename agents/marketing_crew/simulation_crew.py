from pydantic import BaseModel
from crewai import Agent, Crew, Process, Task, LLM
from datetime import datetime
from typing import Dict, List, Optional, Any
from sarah.types import BaseMetrics
import os

class CustomerSegmentMetrics(BaseModel):
    """Model for customer segment metrics"""
    segment_name: str
    demographics: Dict[str, Dict[str, float]]
    behavior_metrics: Dict[str, Any]
    satisfaction_metrics: Dict[str, float]
    lifetime_value: float

class ChannelInsights(BaseModel):
    """Model for channel performance insights"""
    channel_name: str
    performance_metrics: Dict[str, float]

class SimulationOutput(BaseModel):
    """Pydantic model for simulation output metrics and insights"""
    # Channel metrics
    amazon: BaseMetrics
    retail_store: BaseMetrics
    social_media: BaseMetrics
    
    # Customer insights
    customer_insights: Dict[str, Any] = {
        "segments": List[CustomerSegmentMetrics],
        "age_demographics": Dict[str, Dict[str, Any]]
    }
    
    # Channel insights
    channel_insights: Dict[str, Any] = {
        "channels": List[ChannelInsights]
    }

class SimulationCrew:
    """Simulation crew for predicting marketing metrics based on proposed actions"""

    def __init__(self):
        # Get model from environment variable with fallback
        self.llm_model = os.getenv('LLM_MODEL', 'claude-3-5-sonnet-20241022')

    def create_simulation_agent(self):
        simulation_agent = Agent(
            role='Marketing Analytics Expert',
            goal='Predict marketing metrics changes based on historical patterns and proposed actions',
            backstory='Expert in marketing analytics with deep understanding of metric relationships and market dynamics',
            verbose=True,
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            ),
        )
        return simulation_agent

    def create_simulation_task(self, agent: Agent, simulation_input: str, current_metrics: BaseMetrics, expected_outcome: str):
        simulation_task = Task(
            description=f"""
            Current Metrics:
            {current_metrics}

            Proposed Actions:
            {simulation_input}

            Expected Outcome:
            {expected_outcome}

            Requirements:
            1. Analyze the current metrics and proposed actions
            2. Consider market dynamics from the provided context
            3. Predict changes for all channels (amazon, retail_store, social_media):
               - Basic metrics (impressions, clicks, spend, sales, etc.)
               - Customer segment performance
               - Channel-specific insights
            
            4. Generate customer insights for segments:
               - luxury
               - premium
               - mainstream
               - budget
               Including:
               - Demographics distribution
               - Behavior metrics
               - Satisfaction scores
               - Lifetime value
            
            5. Generate age demographic insights for:
               - 18-24
               - 25-34
               - 35-44
               - 45-54
               - 55+
               Including:
               - Population share
               - Purchase frequency
               - Channel preferences
            
            6. Provide channel performance insights:
               - Revenue
               - Growth rate
               - Market share
               - Conversion rate
               - Customer acquisition cost

            Respond with a JSON object containing:
            1. Channel metrics (BaseMetrics structure)
            2. Customer segment insights
            3. Channel performance metrics

            Ensure all metrics are realistic and internally consistent.
            """,
            agent=agent,
            expected_output='JSON with channel metrics, customer insights, and channel performance data',
            output_pydantic=SimulationOutput,
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            ),
        )
        return simulation_task

    def crew(self, simulation_input: str, current_metrics: BaseMetrics, expected_outcome: str) -> Crew:
        """Creates the Simulation crew for metrics prediction"""
        agent = self.create_simulation_agent()
        task = self.create_simulation_task(agent, simulation_input, current_metrics, expected_outcome)
        
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            full_output=True,
            # output_log_file="./simulation_crew.out"
        )
        return crew
