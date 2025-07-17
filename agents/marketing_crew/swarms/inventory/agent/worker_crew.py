from crewai import Agent, Crew, Process, Task, LLM
from pydantic import BaseModel
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime
import os
from datetime import datetime
import time
from swarms.memory.agent import Agent, EntityState, Memory


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


class InventoryWorkerCrew:
    """Worker crew for inventory optimization and management"""

    def __init__(self):
        self.llm_model = os.getenv('LLM_MODEL', 'claude-3-5-sonnet-20241022')
        self.agent_memory = Agent(
            agent_id="inventory_crew",
            swarm_id="inventory_management",
            storage_dir="memories/inventory"
        )

    def create_agent(self):
        return Agent(
            role='Jamie Chen (Inventory Operations Manager)',
            goal="""
            - Achieves growth targets through inventory optimization
            - Ensures optimal stock levels and reorder points
            - Coordinates supply chain activities
            - Manages stock level optimization
            """,
            backstory="""
            Experienced inventory optimization specialist with:
            - 6 years experience in inventory management
            - Expertise in stock level optimization
            - Systematic approach to preventing stockouts
            - Track record of maintaining optimal inventory levels

            Recent Performance Metrics:
            - Q2 2024: 0% stockouts, 2.1 inventory churn
            - Q1 2024: 2% stockouts, 3.6 inventory churn
            - Q4 2023: 4.1% stockouts, 1.7 inventory churn
            """,
            verbose=True,
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            )
        )

    def create_task(self, agent: Agent, inventory_data: Dict) -> Task:
        return Task(
            description=f"""
            Analyze and optimize inventory based on current data:
            {inventory_data}

            Focus Areas:
            1. Immediate inventory actions needed
            2. Stock level optimization
            3. Supply chain risk management
            4. Safety stock adjustments

            Consider:
            - Current stock positions
            - Reorder points
            - Supply chain status
            - Growth targets

            Provide specific recommendations for:
            1. SKU-level actions
            2. Stock level adjustments
            3. Supply chain coordination
            4. Risk mitigation steps
            """,
            agent=agent,
            expected_output="Detailed inventory optimization recommendations",
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            )
        )

    def process(self, inventory_data: Dict) -> Dict:
        """Process inventory data and return optimization recommendations"""
        agent = self.create_agent()
        task = self.create_task(agent, inventory_data)
        
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            full_output=True
        )
        
        result = crew.kickoff()
        
        # Store the interaction in memory
        memory_id = f"inventory_task_{int(time.time())}"
        
        # Extract any actions from the result
        actions = []
        if isinstance(result.raw, dict) and 'actions' in result.raw:
            actions = result.raw['actions']
        
        # Create entity states from inventory data
        entities = [
            EntityState(
                entity_id=sku,
                entity_type="inventory_item",
                attributes=item_data
            )
            for sku, item_data in inventory_data.items()
        ]
        
        # Store memory
        self.agent_memory.create_memory(
            memory_id=memory_id,
            context={
                "inventory_data": inventory_data,
                "task_description": task.description
            },
            prompt=str(task),  # Convert task to string representation
            output={
                "response": result.raw,
                "actions": actions
            },
            agent_state={
                "completed_actions": [],  # To be updated as actions are taken
                "solution_state": {
                    "task_completed": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            entities=entities,
            memory_level="swarm"  # Since this is a crew-level interaction
        )
        
        return result.raw

    def get_task_history(self, start_time: Optional[datetime]=None, end_time: Optional[datetime]=None) -> List[Memory]:
        """Retrieve history of inventory tasks"""
        if start_time and end_time:
            return self.agent_memory.get_memories_by_timerange(start_time, end_time)
        return self.agent_memory.get_all_memories()
