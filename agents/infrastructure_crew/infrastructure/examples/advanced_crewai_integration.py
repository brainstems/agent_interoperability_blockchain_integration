"""
Advanced example of integrating infrastructure agents with CrewAI.

This example demonstrates:
1. Multiple agents with different roles
2. Sequential and hierarchical task execution
3. Tool usage
4. Error handling and retries
5. Real-world business workflow
"""

import asyncio
import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from crewai import Crew, Process
from infrastructure.agents import BaseAgent
from infrastructure.crewai import (
    CrewAIAgentAdapter,
    InfrastructureTask,
    create_csv_search_tool
)

# Configuration
CONFIG = {
    "data_dir": "data",
    "output_dir": "output",
    "llm": {
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000
    },
    "retry": {
        "max_attempts": 3,
        "delay_seconds": 1
    }
}

# Data models
class CustomerSegment(BaseModel):
    segment_id: str
    name: str
    description: str
    size: int
    growth_rate: float

class ProductRecommendation(BaseModel):
    product_id: str
    name: str
    recommendation_score: float
    reasoning: str

class MarketingCampaign(BaseModel):
    campaign_id: str
    name: str
    target_segments: List[CustomerSegment]
    recommended_products: List[ProductRecommendation]
    budget_allocation: Dict[str, float]
    expected_roi: float

# Agent definitions
class MarketAnalystAgent(BaseAgent):
    role = "Market Analyst"
    goal = "Analyze market data and identify customer segments"
    backstory = """
    You are a seasoned market analyst with expertise in customer segmentation
    and market trend analysis. Your insights help identify high-potential
    customer segments for our products.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config=config or {})
        self.tools = [
            create_csv_search_tool(
                csv_path=os.path.join(CONFIG["data_dir"], "customer_data.csv"),
                description="Search customer data for segmentation analysis"
            )
        ]
    
    async def process(self, data: Dict) -> Dict:
        """Process market data and identify segments."""
        # In a real implementation, this would use the tools to analyze data
        return {
            "segments": [
                {
                    "segment_id": "seg1",
                    "name": "Enterprise",
                    "description": "Large enterprises with complex needs",
                    "size": 150,
                    "growth_rate": 0.15
                },
                # More segments...
            ]
        }

class ProductAnalystAgent(BaseAgent):
    role = "Product Analyst"
    goal = "Analyze product performance and make recommendations"
    backstory = """
    You are a product analyst who understands product performance metrics
    and can recommend products based on customer segments and historical data.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config=config or {})
        self.tools = [
            create_csv_search_tool(
                csv_path=os.path.join(CONFIG["data_dir"], "product_performance.csv"),
                description="Search product performance data"
            )
        ]
    
    async def process(self, data: Dict) -> Dict:
        """Process segment data and recommend products."""
        # In a real implementation, this would use the tools to analyze data
        return {
            "recommendations": [
                {
                    "product_id": "prod1",
                    "name": "AI Analytics Suite",
                    "recommendation_score": 0.92,
                    "reasoning": "High match with enterprise needs"
                },
                # More recommendations...
            ]
        }

class MarketingStrategistAgent(BaseAgent):
    role = "Marketing Strategist"
    goal = "Develop marketing campaigns based on segments and products"
    backstory = """
    You are a marketing strategist who creates effective campaigns
    based on customer segments and product recommendations.
    """
    
    async def process(self, data: Dict) -> Dict:
        """Create a marketing campaign."""
        return {
            "campaign": {
                "campaign_id": "camp1",
                "name": "Enterprise AI Solutions",
                "target_segments": data.get("segments", []),
                "recommended_products": data.get("recommendations", []),
                "budget_allocation": {
                    "digital": 0.6,
                    "events": 0.25,
                    "content": 0.15
                },
                "expected_roi": 4.2
            }
        }

async def main():
    """Run the advanced crewAI integration example."""
    # Create our agents
    market_analyst = MarketAnalystAgent()
    product_analyst = ProductAnalystAgent()
    marketing_strategist = MarketingStrategistAgent()
    
    # Create tasks with dependencies
    analyze_market_task = InfrastructureTask(
        agent=market_analyst,
        description="Analyze the market and identify customer segments",
        expected_output="A list of customer segments with their characteristics"
    )
    
    analyze_products_task = InfrastructureTask(
        agent=product_analyst,
        description="Analyze product performance and make recommendations",
        expected_output="Product recommendations for each customer segment",
        context=[analyze_market_task]  # Depends on market analysis
    )
    
    create_campaign_task = InfrastructureTask(
        agent=marketing_strategist,
        description="Create a marketing campaign based on segments and products",
        expected_output="A complete marketing campaign plan",
        context=[analyze_market_task, analyze_products_task]  # Depends on both
    )
    
    # Create and run the crew
    crew = Crew(
        agents=[
            CrewAIAgentAdapter(agent) 
            for agent in [market_analyst, product_analyst, marketing_strategist]
        ],
        tasks=[
            analyze_market_task,
            analyze_products_task,
            create_campaign_task
        ],
        process=Process.sequential,
        verbose=True
    )
    
    # Run the crew with input data
    input_data = {
        "market": "AI software",
        "region": "global",
        "timeframe": "Q3 2023"
    }
    
    print("Starting campaign planning...")
    result = await crew.kickoff(inputs=input_data)
    
    # Save the results
    os.makedirs(CONFIG["output_dir"], exist_ok=True)
    output_file = os.path.join(CONFIG["output_dir"], "campaign_plan.json")
    
    with open(output_file, "w") as f:
        import json
        json.dump(result, f, indent=2)
    
    print(f"\nCampaign planning completed! Results saved to {output_file}")
    return result

if __name__ == "__main__":
    asyncio.run(main())
