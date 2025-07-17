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


class CornFlakesRecommendations(BaseModel):
    customer_profile: CustomerProfile
    channel_strategy: List[ChannelPerformance]
    retail_strategy: List[RetailStrategy]
    advertising_recommendations: Dict[str, Any]
    timestamp: datetime


class CornFlakesCrew:
    """Crew for Classic Corn Flakes product strategy"""

    def __init__(self):
        # Get model from environment variable with fallback
        self.llm_model = os.getenv('LLM_MODEL', 'claude-3-5-sonnet-20241022')

    def create_product_agent(self):
        product_agent = Agent(
            role='Classic Corn Flakes Product Specialist',
            goal="""Optimize Classic Corn Flakes market performance across all channels with focus on:
                   - Customer targeting
                   - Channel optimization
                   - Retail strategy
                   - Advertising allocation""",
            backstory="""Experienced product specialist with deep understanding of:
                        - Cereal market dynamics
                        - Multi-channel retail strategy
                        - Consumer behavior analysis
                        - Amazon advertising optimization
                        Successfully grew Classic Corn Flakes market share by 15% in previous quarter.""",
            verbose=True,
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            ),
        )
        return product_agent

    def create_task_callback(self, redis_client, task_type: str):

        def callback_function(output: TaskOutput):

            # print(f"Callback function called for {task_type} with output: {output.raw}")
            
            redis_client.rpush("api_queue", json.dumps({
                "message": f"Completed {task_type} analysis for Classic Corn Flakes {output.raw}",
                "type": f"task_update_corn_flakes_{task_type}",
                "timestamp": datetime.now().isoformat()
            }))
                
        return callback_function

    def create_product_tasks(self, agent: Agent, current_metrics: Dict[str, Any], redis_client):
        tasks = []
        
        # Task 1: Customer Profile Analysis
        customer_profile_task = Task(
            description=f"""
            Analyze customer data for Classic Corn Flakes:

            Current Metrics:
            {current_metrics}

            Key Market Inputs:
            - Dietary Trends: High preference for non-GMO cereals
            - Target Demographics: Households with children aged 5-12
            - Regional Focus: High interest in Philadelphia Region
            - Product Features: Classic Corn Flakes is non-GMO certified

            Requirements:
            1. Create detailed ideal customer profile considering:
               - Dietary preferences and trends
                 * Non-GMO preference patterns
                 * Health consciousness levels
                 * Breakfast habits
               - Demographic patterns
                 * Households with children 5-12
                 * Family size and composition
                 * Income levels in target region
               - Regional demand variations
                 * Philadelphia Region specifics
                 * Suburban vs urban preferences
                 * Regional competition analysis
               - Purchase behaviors
                 * Shopping frequency
                 * Pack size preferences
                 * Price sensitivity

            2. Provide specific insights on:
               - Key customer attributes
                 * Family composition
                 * Lifestyle patterns
                 * Shopping habits
               - Purchase motivations
                 * Health considerations
                 * Price sensitivity
                 * Brand loyalty factors
               - Brand perception
                 * Non-GMO positioning
                 * Family-friendly appeal
                 * Value proposition
               - Price sensitivity
                 * Regional pricing analysis
                 * Competitor price points
                 * Value perception
               - Health consciousness
                 * Non-GMO awareness
                 * Nutritional priorities
                 * Dietary preferences

            3. Recommend marketing message adaptations for:
               - Different demographic segments
                 * Parents of young children
                 * Health-conscious families
                 * Value seekers
               - Various sales channels
                 * Grocery stores in Philadelphia
                 * Online platforms
                 * Direct marketing
               - Regional markets
                 * Philadelphia-specific messaging
                 * Suburban vs urban targeting
                 * Local event tie-ins
               - Seasonal variations
                 * Back-to-school promotions
                 * Holiday campaigns
                 * Summer activities

            Format response as structured customer profile with actionable recommendations.
            Focus on the Philadelphia Region market and families with school-age children.
            Emphasize non-GMO messaging and family-friendly positioning.
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
            Evaluate advertising channel performance for Classic Corn Flakes:

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
            Develop retail strategy for Classic Corn Flakes:

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
            # output_pydantic=CornFlakesRecommendations,
            callback=self.create_task_callback(redis_client, "advertising")
        )
        tasks.append(advertising_task)

        return tasks

    def crew(self, current_metrics: Dict[str, Any], redis_client) -> Crew:
        """Creates the Corn Flakes Strategy crew"""
        agent = self.create_product_agent()
        tasks = self.create_product_tasks(agent, current_metrics, redis_client)
        
        crew = Crew(
            agents=[agent],
            tasks=tasks,
            verbose=True,
            full_output=True
        )
        return crew 
