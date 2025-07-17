from crewai import Agent, Crew, Process, Task, LLM
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
from crewai.tasks.task_output import TaskOutput
import os


class CustomerProfile(BaseModel):
    demographics: Dict[str, Any]
    preferences: Dict[str, Any]
    behaviors: Dict[str, Any]
    marketing_recommendations: List[str]


class ChannelPerformance(BaseModel):
    channel_name: str
    metrics: Dict[str, float]
    recommendations: List[str]
    priority_score: float


class RetailStrategy(BaseModel):
    location_name: str
    strengths: List[str]
    challenges: List[str]
    recommendations: List[str]
    priority_level: int


class ProductRecommendations(BaseModel):
    customer_profile: CustomerProfile
    channel_strategy: List[ChannelPerformance]
    retail_strategy: List[RetailStrategy]
    advertising_recommendations: Dict[str, Any]
    timestamp: datetime


class ProductWorkerCrew:
    """Crew for product strategy and optimization"""

    def __init__(self, product_name: str="Classic Corn Flakes"):
        self.product_name = product_name
        self.llm_model = os.getenv('LLM_MODEL', 'claude-3-5-haiku-20241022')

    def create_product_agent(self):
        product_agent = Agent(
            role=f'{self.product_name} Product Specialist',
            goal=f"""Optimize {self.product_name} market performance across all channels with focus on:
                   - Customer targeting
                   - Channel optimization
                   - Retail strategy
                   - Advertising allocation""",
            backstory="""Experienced product specialist with deep understanding of:
                        - Market dynamics
                        - Multi-channel retail strategy
                        - Consumer behavior analysis
                        - Amazon advertising optimization
                        Successfully grew product market share by 15% in previous quarter.""",
            verbose=True,
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            ),
        )
        return product_agent

    def create_task_callback(self, redis_client, task_type: str):

        def callback_function(output: TaskOutput):
            redis_client.rpush("api_queue", json.dumps({
                "message": f"Completed {task_type} analysis for {self.product_name} {output.raw}",
                "type": f"task_update_product_{task_type}",
                "swarm_name": "product_agent",
                "timestamp": datetime.now().isoformat()
            }))

        return callback_function

    def create_product_tasks(self, agent: Agent, current_metrics: Dict[str, Any], redis_client):
        tasks = []
        
        # Task 1: Customer Profile Analysis
        customer_profile_task = Task(
            description=f"""
            Analyze customer data for {self.product_name}:

            Current Metrics:
            {current_metrics}

            Requirements:
            1. Create detailed ideal customer profile considering:
               - Dietary preferences and trends
               - Demographic patterns
               - Regional demand variations
               - Purchase behaviors

            2. Provide specific insights on:
               - Key customer attributes
               - Purchase motivations
               - Brand perception
               - Price sensitivity
               - Product preferences

            3. Recommend marketing message adaptations for:
               - Different demographic segments
               - Various sales channels
               - Regional markets
               - Seasonal variations

            Format response as structured customer profile with actionable recommendations.
            """,
            agent=agent,
            expected_output="Structured customer profile with demographics, preferences, and recommendations in JSON format",
            # output_pydantic=CustomerProfile,
            callback=self.create_task_callback(redis_client, "customer_profile"),
            async_execution=True
        )
        tasks.append(customer_profile_task)

        # Task 2: Channel Performance Analysis
        channel_analysis_task = Task(
            description=f"""
            Evaluate advertising channel performance for {self.product_name}:

            Current Performance:
            {current_metrics}

            Requirements:
            1. Analyze performance metrics for each channel:
               - Amazon
               - Retail Store
               - Social Media

            2. Compare metrics including:
               - Click-through rates
               - Conversion rates
               - Customer acquisition costs
               - Return on ad spend
               - Customer lifetime value

            3. Provide recommendations for:
               - Budget allocation
               - Content optimization
               - Targeting improvements
               - Cross-channel synergies

            Rank channels by effectiveness and provide specific optimization strategies.
            """,
            agent=agent,
            expected_output="Channel performance analysis with metrics and recommendations in JSON format",
            # output_pydantic=ChannelPerformance,
            callback=self.create_task_callback(redis_client, "channel_analysis"),
            async_execution=True
        )
        tasks.append(channel_analysis_task)

        # Task 3: Retail Strategy Development
        retail_strategy_task = Task(
            description=f"""
            Develop retail strategy for {self.product_name}:

            Current Data:
            {current_metrics}

            Requirements:
            1. Evaluate retail locations considering:
               - Regional demand patterns
               - Shelf space availability
               - Customer demographics
               - Competition presence

            2. Analyze performance factors:
               - Sales velocity
               - Stock availability
               - Display effectiveness
               - Customer feedback

            3. Provide recommendations for:
               - Location prioritization
               - Inventory management
               - Display optimization
               - Promotional coordination

            Create prioritized retail strategy with specific action items.
            """,
            agent=agent,
            expected_output="Retail strategy with location analysis and recommendations in JSON format",
            # output_pydantic=RetailStrategy,
            callback=self.create_task_callback(redis_client, "retail_strategy"),
            async_execution=True
        )
        tasks.append(retail_strategy_task)

        # Task 4: Advertising Budget Advocacy
        advertising_task = Task(
            description=f"""
            Develop advertising budget allocation strategy:

            Current Metrics:
            {current_metrics}

            Requirements:
            1. Analyze competitive positioning:
               - Share of voice
               - Ad spend comparison
               - Performance metrics
               - Market share trends

            2. Build case for budget allocation:
               - ROI analysis
               - Growth opportunities
               - Competitive threats
               - Market potential

            3. Provide specific recommendations for:
               - Budget increases
               - Allocation across channels
               - Timing of spend
               - Performance targets

            Create compelling argument for advertising investment with supporting data.
            """,
            agent=agent,
            expected_output="Advertising budget recommendations with supporting analysis in JSON format",
            # output_pydantic=ProductRecommendations,
            callback=self.create_task_callback(redis_client, "advertising")
        )
        tasks.append(advertising_task)

        return tasks

    def process(self, data: Dict[str, Any]) -> Dict:
        """Process product strategy analysis"""
        agent = self.create_product_agent()
        tasks = self.create_product_tasks(agent, data.get('metrics', {}), data.get('redis_client'))
        
        crew = Crew(
            agents=[agent],
            tasks=tasks,
            verbose=True,
            full_output=True
        )
        
        result = crew.kickoff()
        return result.raw
