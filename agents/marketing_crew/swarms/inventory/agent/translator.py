from crewai import Agent, Crew, Process, Task, LLM
from typing import List, Dict, Optional
from datetime import datetime
import os

class InventoryTranslationAgent:
    """Translation agent for inventory management and optimization"""

    def __init__(self):
        self.llm_model = os.getenv('LLM_MODEL', 'claude-3-5-haiku-20241022')

    def create_agent(self):
        return Agent(
            role='Inventory Management Expert',
            goal="""Analyze inventory data and create optimization strategies.
                   Focus on stock level management, reorder points, and supply chain efficiency.""",
            backstory="""Senior inventory management specialist with 8 years of experience.
                        Expert in stock optimization, inventory forecasting, and supply chain management.
                        Successfully reduced stockouts by 98% and improved inventory turnover by 25%.""",
            verbose=True,
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            ),
        )

    def create_task(self, agent: Agent, message: str):
        return Task(
            description=f"""
            Analyze the following inventory message and provide optimization recommendations:

            Message:
            {message}

            Requirements:
            1. Analyze current inventory levels and trends
            2. Consider key metrics:
               - Stock turnover rate
               - Order fulfillment rate
               - Lead time performance
               - Safety stock levels
            3. Identify optimization opportunities
            4. Provide actionable recommendations

            Format the response as a JSON with the following structure:
            {{
                "timestamp": "<ISO format timestamp>",
                "inventory_analysis": {{
                    "current_state": {{
                        "stock_levels": [],
                        "turnover_metrics": [],
                        "fulfillment_metrics": []
                    }},
                    "trends": {{
                        "stock_movement": [],
                        "demand_patterns": [],
                        "seasonal_factors": []
                    }},
                    "risks": {{
                        "stockout_risks": [],
                        "overstock_risks": [],
                        "supply_chain_risks": []
                    }}
                }},
                "optimization_recommendations": {{
                    "immediate_actions": [],
                    "short_term_plans": [],
                    "long_term_strategy": []
                }},
                "implementation_plan": {{
                    "priority_actions": [],
                    "resource_requirements": [],
                    "timeline": [],
                    "expected_outcomes": []
                }}
            }}
            """,
            agent=agent,
            expected_output='JSON formatted inventory analysis and recommendations',
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            ),
        )

    def process(self, message: str) -> Dict:
        """Process the inventory message and return optimization recommendations"""
        agent = self.create_agent()
        task = self.create_task(agent, message)
        
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            full_output=True
        )
        
        result = crew.kickoff()
        return result.raw