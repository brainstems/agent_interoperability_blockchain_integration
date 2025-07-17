from crewai import Agent, Crew, Process, Task, LLM
from datetime import datetime
import os


class WorkerCrew:
    """Worker crew for processing promotional tasks"""
    
    def __init__(self, worker_name: str):
        self.worker_name = worker_name
        self.llm_model = os.getenv('LLM_MODEL', 'claude-3-5-sonnet-20241022')

    def create_worker_agent(self):
        worker_agent = Agent(
            role=f'Marketing Specialist {self.worker_name}',
            goal="""
            - Analyze and process promotional tasks
            - Evaluate feasibility and potential impact
            - Provide detailed implementation recommendations
            - Assess risks and resource requirements
            """,
            backstory=f"""
            Experienced marketing specialist with expertise in:
            - Promotional strategy execution
            - Campaign performance analysis
            - Market trend evaluation
            - Risk assessment and mitigation
            
            As Marketing Specialist {self.worker_name}, focuses on:
            - Detailed promotional task analysis
            - Implementation planning
            - Resource allocation optimization
            - Performance metrics evaluation
            """,
            verbose=True,
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            )
        )
        return worker_agent

    def create_worker_task(self, agent: Agent, input_data: dict):
        worker_task = Task(
            description=f"""
            Analyze the following promotional task and provide detailed recommendations:
            
            Input Task Data:
            {input_data}
            
            Provide analysis covering:
            1. Task feasibility assessment
            2. Resource requirements
            3. Implementation timeline
            4. Expected outcomes
            5. Risk factors
            6. Required coordination points
            
            Focus on practical execution details and measurable outcomes.
            """,
            agent=agent,
            expected_output="""
            Detailed analysis in JSON format with:
            {
                "task_id": "<original task id>",
                "worker_name": "<worker name>",
                "analysis": {
                    "feasibility_score": float,
                    "resource_requirements": list,
                    "timeline_days": int,
                    "expected_outcomes": dict,
                    "risk_factors": list,
                    "coordination_needs": list
                },
                "recommendations": list,
                "timestamp": "<ISO format timestamp>"
            }
            """,
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            )
        )
        return worker_task

    def process(self, input_data: dict) -> dict:
        """Process the input task using the worker crew"""
        agent = self.create_worker_agent()
        task = self.create_worker_task(agent, input_data)
        
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff()
        
        # Ensure proper formatting and add metadata
        return {
            **result.raw,
            "worker_name": self.worker_name,
            "swarm_name": input_data.get('swarm_name', 'promotional'),
            "timestamp": datetime.now().isoformat()
        } 
