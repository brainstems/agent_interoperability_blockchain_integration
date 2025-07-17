from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from pydantic import BaseModel
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime
import os

class PromotionType(Enum):
    SEASONAL = "seasonal"
    CLEARANCE = "clearance"
    NEW_PRODUCT = "new_product"
    BUNDLE = "bundle"
    FLASH_SALE = "flash_sale"
    INVENTORY_DRIVEN = "inventory_driven"

class PromotionTiming(Enum):
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    CONDITIONAL = "conditional"

class PromotionChannel(Enum):
    AMAZON = "amazon"
    RETAIL_STORE = "retail_store"
    SOCIAL_MEDIA = "social_media"
    CROSS_CHANNEL = "cross_channel"

class PromotionalAction(BaseModel):
    sku: str
    action_type: str
    priority: int  # 1 (highest) to 3 (lowest)
    timing: PromotionTiming
    channel: PromotionChannel
    discount_percentage: Optional[float]
    duration_days: int
    min_inventory_required: int
    target_roas: float
    budget_allocation: float
    expected_lift: float
    action_items: List[str]

class PromotionalStrategy(BaseModel):
    type: PromotionType
    priority: int
    impact: float  # Estimated impact percentage
    effort: int    # 1 (easy) to 3 (complex)
    description: str
    channels: List[PromotionChannel]
    timing_strategy: PromotionTiming
    inventory_requirements: Dict[str, int]
    budget_requirements: float
    expected_roas: float
    risk_level: float  # 0 to 1
    actions: List[PromotionalAction]

class PromotionalRecommendations(BaseModel):
    timestamp: datetime
    strategies: List[PromotionalStrategy]
    total_budget_impact: float
    expected_revenue_lift: float
    inventory_impact: Dict[str, Dict[str, float]]
    risk_assessment: Dict[str, float]
    coordination_requirements: List[str]

class PromotionQueue:
    """Promotion management queue for store optimization and campaign execution"""

    def __init__(self):
        # Get model from environment variable with fallback
        self.llm_model = os.getenv('LLM_MODEL', 'claude-3-5-sonnet-20241022')

    def create_promotion_team(self):
        promotion_agent = Agent(
            role='Marcus Rodriguez (Amazon Store Experience Manager)',
            goal="""
            - Optimizes Amazon Store layout and content
            - Achieves 3% growth in store-driven sales
            - Improves conversion rates and average order value
            - Manages product discovery optimization
            """,
            backstory="""
            Experienced store optimization specialist with:
            - 5 years Amazon Store optimization expertise
            - A/B testing and content strategy specialist
            - Expert in store layout optimization
            - Specialized in conversion rate optimization
            - Track record of achieving 3% growth targets through store optimization

            Marcus has overperformed the last 3 quarters:

            | Qtr          | Budget  | Revenue Goals | ROAS  |
            |--------------|---------|---------------|--------|
            | 2nd Qtr; 2024| -3.1%   | +3.2%        | +6%   |
            | 1st Qtr; 2024| -2.3%   | +3.6%        | +8%   |
            | 4th Qtr; 2023| 0%      | +3.8%        | +14%  |
            """,
            verbose=True,
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            )
        )
        return promotion_agent

    def create_promotion_tasks(self, agent: Agent):
        promotion_task = Task(
            description="""
            Analyze current store performance and promotional opportunities to:
            1. Identify optimal store layout improvements
            2. Design content-driven promotional strategies
            3. Optimize product discovery and placement
            4. Calculate conversion rate impact
            5. Plan A/B testing strategy

            Focus areas:
            - Store layout optimization
            - Content strategy enhancement
            - Product discovery improvement
            - Conversion rate optimization
            - A/B testing coordination
            """,
            agent=agent,
            expected_output="""
            Detailed store optimization recommendations including:
            - Layout and content strategies
            - Product placement recommendations
            - A/B testing plans
            - Expected performance metrics
            - Implementation timeline
            """,
            output_pydantic=PromotionalRecommendations,
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            )
        )
        return promotion_task

    def crew(self) -> Crew:
        """Creates the Promotional Strategy crew"""
        agent = self.create_promotion_team()
        task = self.create_promotion_tasks(agent)
        
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            full_output=True,
            output_log_file="./promotion_crew.out"
        )
        return crew 