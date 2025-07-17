from pydantic import BaseModel
from datetime import datetime
from crewai import Agent, Crew, Process, Task
from langchain_anthropic import ChatAnthropic
from typing import List, Dict, Optional
from enum import Enum
import os

class SalesToInventoryTranslationCrew():
    """Translation crew for converting sales messages to inventory events"""

    def __init__(self):
        # Get model from environment variable with fallback
        self.llm_model = os.getenv('LLM_MODEL', 'claude-3-5-sonnet-20241022')

    def create_translation_agent(self):
        translation_agent = Agent(
            role='Promotional Products Strategy Expert',
            goal="""Optimize promotional timing and inventory management to achieve 3% growth while maintaining optimal stock levels.
                   Focus on preventing stockouts and aligning marketing spend with inventory positions.""",
            backstory="""Seasoned professional with 6 years of experience bridging inventory and marketing domains. 
                        Demonstrated success in promotional timing and preventing stockouts, with a proven track record 
                        of maintaining optimal stock levels during promotions. Recently achieved significant improvements 
                        in inventory management with 0% stockouts in Q2 2024 and consistent optimization of ad spend.""",
            verbose=True,
            llm=ChatAnthropic(
                model=self.llm_model,
                temperature=0.2
            ),
        )
        return translation_agent

    def create_translation_task(self, agent: Agent, original_message: str):
        translation_task = Task(
            description=f"""
            Source Domain: sales and promotional planning
            Target Domain: inventory management

            Original Message:
            {original_message}

            Requirements:
            1. Transform this message with focus on inventory implications of promotional activities
            2. Consider recent performance metrics:
               - Current inventory churn rate: 2.1
               - Stock level optimization: 0% out of stock
               - Ad spend efficiency: -3% vs target
            3. Ensure alignment between promotional calendar and inventory positions
            4. Include specific inventory requirements for projected 3% growth target
            5. Highlight any potential stockout risks based on promotional plans

            Transform this message into a JSON format with the following structure:
            {{
                "timestamp": "<ISO format timestamp>",
                "sku_status": {{
                    "<sku_id>": {{
                        "current_stock": <int>,
                        "reorder_point": <int>,
                        "safety_stock": <int>,
                        "lead_time_days": <int>,
                        "daily_velocity": <float>,
                        "promo_multiplier": <float>,
                        "stock_coverage_days": <float>,
                        "alerts": ["low_stock", "stockout_risk", etc.]
                    }}
                }},
                "promotional_impact": {{
                    "impacted_skus": [],
                    "risk_assessment": [],
                    "required_actions": []
                }},
                "supply_chain_status": {{
                    "open_orders": [],
                    "lead_time_updates": [],
                    "fulfillment_risks": [],
                    "coordination_actions": []
                }},
                "recommendations": []
            }}

            Ensure all numerical values are appropriate for inventory context and alerts match the InventoryAlert enum options.
            """,
            agent=agent,
            expected_output='JSON formatted inventory status and recommendations',
        )
        return translation_task

    def crew(self, original_message: str) -> Crew:
        """Creates the Translation crew for sales to inventory"""
        agent = self.create_translation_agent()
        task = self.create_translation_task(agent, original_message)
        
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            full_output=True,
            # output_log_file="./translation_crew_sales_to_inventory.out"
        )
        return crew

class SalesToPromotionalTranslationCrew():
    """Translation crew for converting sales messages to promotional strategy events"""

    def __init__(self):
        # Get model from environment variable with fallback
        self.llm_model = os.getenv('LLM_MODEL', 'claude-3-5-sonnet-20241022')

    def create_translation_agent(self):
        translation_agent = Agent(
            role='Amazon Store Experience Manager',
            goal="""Optimize store layout and content strategy to achieve 3% growth while improving conversion rates.
                   Focus on product discovery, A/B testing, and maintaining strong ROAS metrics.""",
            backstory="""Experienced Amazon Store optimization specialist with 5 years expertise in A/B testing and 
                        content strategy. Proven track record of exceeding revenue goals while maintaining efficient 
                        budget spend, demonstrated by +3.2% revenue growth and 6% ROAS in Q2 2024.""",
            verbose=True,
            llm=ChatAnthropic(
                model=self.llm_model,
                temperature=0.2
            ),
        )
        return translation_agent

    def create_translation_task(self, agent: Agent, original_message: str):
        translation_task = Task(
            description=f"""
            Source Domain: sales planning
            Target Domain: promotional strategy and store optimization

            Original Message:
            {original_message}

            Requirements:
            1. Transform this message with focus on store layout and promotional implications
            2. Consider recent performance metrics:
               - Current ROAS: +6%
               - Revenue Growth: +3.2%
               - Budget Performance: -3.1%
            3. Ensure alignment between store layout changes and promotional calendar
            4. Include specific promotional requirements for projected 3% growth target
            5. Highlight optimization opportunities based on current store performance

            Transform this message into a JSON format with the following structure:
            {{
                "timestamp": "<ISO format timestamp>",
                "store_status": {{
                    "current_layout": {{
                        "conversion_rate": <float>,
                        "avg_order_value": <float>,
                        "product_discovery_score": <float>,
                        "optimization_opportunities": []
                    }},
                    "ab_tests": {{
                        "active_tests": [],
                        "test_results": [],
                        "recommended_changes": []
                    }}
                }},
                "promotional_strategy": {{
                    "target_products": [],
                    "placement_recommendations": [],
                    "content_updates": []
                }},
                "performance_metrics": {{
                    "roas_targets": [],
                    "growth_projections": [],
                    "budget_allocation": []
                }},
                "recommendations": []
            }}

            Ensure all metrics align with current performance and growth targets.
            """,
            agent=agent,
            expected_output='JSON formatted promotional strategy and recommendations',
        )
        return translation_task

    def crew(self, original_message: str) -> Crew:
        """Creates the Translation crew for sales to promotional strategy"""
        agent = self.create_translation_agent()
        task = self.create_translation_task(agent, original_message)
        
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            full_output=True,
        )
        return crew


