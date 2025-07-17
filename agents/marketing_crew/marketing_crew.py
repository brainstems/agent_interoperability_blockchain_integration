from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from pydantic import BaseModel
from enum import Enum
from typing import List, Dict
import os

from tools.revenue_performance_generator import RevenuePerformanceGenerator
from tools.campaign_recommendation_engine import CampaignRecommendationEngine
from tools.campaign_performance_tracker import CampaignPerformanceTracker
from tools.budget_monitor import BudgetMonitor
from tools.inventory_tracker import InventoryTracker
from tools.growth_trajactor import GrowthTrajectoryForecaster
from sarah.types import BaseMetrics, InventoryData

# class RecommendationType(Enum):
#     BUDGET = "budget"
#     TARGETING = "targeting"
#     CREATIVE = "creative"
#     GROWTH = "growth"


class CampaignRecommendation(BaseModel):
    type: str
    priority: int  # 1 (highest) to 3 (lowest)
    impact: float  # Estimated impact percentage
    effort: int  # 1 (easy) to 3 (complex)
    description: str
    action_items: List[str]
    estimated_roi: float


class CampaignRecommendations(BaseModel):
    recommendations: List[CampaignRecommendation]


class MarketingCrew():
    """Marketing crew for campaign planning and execution"""
    
    def __init__(self):
        # Get model from environment variable with fallback
        self.llm_model = os.getenv('LLM_MODEL', 'claude-3-5-sonnet-20241022')

    def create_marketing_team(self, budget: float, growth_rate: float):
        sarah_marketing_agent = Agent(
            role='Sarah Chen (Amazon Advertising Manager)',
            goal=f"""Goal:
              - Drives {growth_rate*100}% growth through Amazon Advertising campaigns for 4th qtr 2024 with a total budget of ${budget}
              - Maintains ROAS above industry benchmark
              - Coordinates sponsored products, brands, and display advertising
            """,
            backstory="""
  - 8 years Amazon marketing experience
  - Proven track record of exceeding growth targets
  - Data-driven decision maker with focus on ROAS
  - Specialized in coordinating sponsored product campaigns with brand initiatives
  - Expert in 48-hour performance window optimization
  - Sarah has underperformed the last 3 quarters by overspending her budget and not achieving revenue goals

            | Qtr          | Ad Spend | Revenue Goals | ROAS |
            |--------------|----------|---------------|------|
            | 2nd Qtr; 2024| +3.6%    | -3%           | -9%  |
            | 1st Qtr; 2024| +1.3%    | -2.3%         | -12% |
            | 4th Qtr; 2023| +5%      | 0%            | -15% |
            """,
            verbose=True,
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            ),
        )
        return sarah_marketing_agent

    def create_marketing_tasks(self, agent: Agent, historical_descisions: str, current_metrics_channels: Dict[str, BaseMetrics], budget: float, growth_rate: float, current_date: str, inventory_data: InventoryData):
        sarah_marketing_task = Task(
            description=f"""
            You are assisting Sarah Chen, Amazon Advertising Manager at FoodSmart™.

            Historical Context:
            Sarah's typical approach includes:
            - Focuses on 48-hour performance windows for optimization decisions
            - Prioritizes data-driven adjustments with minimum 25% confidence intervals
            - Maintains strict ROAS thresholds while testing growth opportunities
            - History of successful coordination with inventory teams during promotions

            Historical Data and Descisions based on metrics:
            {historical_descisions}


            Current Metrics:
            {current_metrics_channels}

            Current Date:
            {current_date}

            Inventory Data:
            {inventory_data}

            Sarah has 3 marketing channels:
            - amazon
            - retail_store
            - social_media


            Based on Sarah's historical decision-making patterns and current data:
            1. What optimizations would she prioritize given her preference for 48-hour performance windows?
            2. How would she typically balance the current 3.8x ROAS with the need to accelerate growth from 2.8% to 3.0%?
            3. What risks would she identify and mitigate based on her historical approach?
            4. How would she coordinate with inventory teams given the projected velocity increase?

            Craft a response that reflects Sarah's:
            - Data-driven decision making style
            - Focus on balanced ROAS and growth metrics
            - Proactive coordination with inventory teams
            - Systematic testing methodology

            Provide specific recommendations aligned with her measured approach to budget allocation and current performance data.
            """,
            agent=agent,
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            ),
            expected_output="""
                Create a detailed execution plan for the marketing campaign, specific recommendations for 
                1. budget allocation for current date based on ROAS and growth rate
                2. performance optimization for every channel based on ROAS and growth rate

                # class RecommendationType(Enum):
            #     BUDGET = "budget"
            #     TARGETING = "targeting"
            #     CREATIVE = "creative"
            #     GROWTH = "growth"
            In JSON format
            """,
            output_pydantic=CampaignRecommendations
        )
        return sarah_marketing_task

    def crew(self, historical_descisions: str, current_metrics_channels: Dict[str, BaseMetrics], budget: float, growth_rate: float, current_date: str, inventory_data: InventoryData) -> Crew:
        """Creates the Marketing crew for multiple channels"""

        # agents = []
        # tasks = []

        agent = self.create_marketing_team(budget, growth_rate)
        task = self.create_marketing_tasks(agent, historical_descisions, current_metrics_channels, budget, growth_rate, current_date, inventory_data)
        
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            full_output=False
        )
        return crew 
