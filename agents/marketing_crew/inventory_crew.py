from crewai import Agent, Crew, Process, Task, LLM
from pydantic import BaseModel
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime
import json
import os


# Define the output types
class ActionPriority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionType(Enum):
    INVENTORY_PROTECTION = "inventory_protection"
    GROWTH_OPTIMIZATION = "growth_optimization"
    SUPPLY_CHAIN_ALIGNMENT = "supply_chain_alignment"
    REORDER = "reorder"
    PROMOTIONAL = "promotional"
    BUDGET_ADJUSTMENT = "budget_adjustment"


class InventoryAction(BaseModel):
    sku: str
    type: str
    priority: str
    description: str
    quantity: Optional[int] = None
    timing: Optional[str] = None
    impact: Optional[float] = None
    action_items: List[str]


class InventoryRecommendation(BaseModel):
    timestamp: datetime
    sku: str
    type: str
    priority: str
    current_status: Dict
    recommended_actions: List[InventoryAction]
    expected_impact: Dict


class InventoryRecommendations(BaseModel):
    recommendations: List[InventoryRecommendation]


class InventoryCrew:
    """Inventory management crew for stock optimization and promotional coordination"""

    def __init__(self):
        # Get model from environment variable with fallback
        self.llm_model = os.getenv('LLM_MODEL', 'claude-3-5-sonnet-20241022')

    def create_inventory_agent(self):
        inventory_manager = Agent(
            role='Jamie Chen (Inventory Operations Manager)',
            goal="""
            - Achieves 3% growth through strategic product promotion
            - Ensures optimal inventory levels align with promotional activities
            - Coordinates promotional calendars with inventory positions
            - Manages stock level optimization
            """,
            backstory="""
            Experienced inventory optimization specialist with:
            - 6 years experience bridging inventory and marketing
            - Expertise in promotional timing
            - Systematic approach to preventing stockouts
            - Specialized in scaling ad spend based on inventory
            - Track record of maintaining optimal stock levels during promotions

            Jamie has performed well over the last 3 quarters:

            | Qtr          | Inventory Churns | Out of Stock | Adspend |
            |--------------|------------------|--------------|----------|
            | 2nd Qtr; 2024| 2.1             | 0%          | -3%     |
            | 1st Qtr; 2024| 3.6             | +2%         | -5%     |
            | 4th Qtr; 2023| 1.7             | +4.1%       | -6%     |
            """,
            verbose=True,
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            )
        )
        return inventory_manager

    def create_inventory_tasks(self, agent: Agent, inventory_data: Dict) -> Task:
        inventory_task = Task(
            description=f"""
            You are assisting Jamie Chen, Inventory Operations Manager at FoodSmart™.

            Historical Context:
            Jamie's typical approach includes:
            - Focuses on stock coverage and velocity trends
            - Maintains strict inventory controls during promotions
            - Coordinates closely with marketing for promotional timing
            - Implements data-driven reorder strategies

            Current Inventory Data:
            {json.dumps(inventory_data, indent=4)}

            Based on Jamie's historical performance and current data:
            1. What immediate inventory actions are needed based on current stock levels and alerts?
            2. How should promotional timing be coordinated with current inventory positions?
            3. What supply chain risks need to be addressed?
            4. How should safety stock levels be adjusted for upcoming promotions?

            Craft recommendations that reflect Jamie's:
            - Data-driven inventory management style
            - Focus on preventing stockouts while minimizing excess
            - Proactive coordination with marketing teams
            - Systematic approach to promotional inventory planning

            Provide specific recommendations aligned with:
            - Current stock positions
            - Promotional calendar
            - Supply chain status
            - Growth targets
            """,
            agent=agent,
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            ),
            expected_output="""
                Create detailed inventory management recommendations including:
                1. Immediate actions needed for at-risk SKUs
                2. Promotional timing recommendations
                3. Supply chain coordination steps
                4. Safety stock adjustments
              In JSON format
            """,
            output_pydantic=InventoryRecommendations
        )
        return inventory_task

    def crew(self, inventory_data: Dict) -> Crew:
        """Creates the Inventory Management crew"""
        
        agent = self.create_inventory_agent()
        task = self.create_inventory_tasks(agent, inventory_data)
        
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            full_output=False
        )
        return crew
