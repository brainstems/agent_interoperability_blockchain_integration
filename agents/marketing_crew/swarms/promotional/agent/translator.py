from crewai import Agent, Crew, Process, Task, LLM
from datetime import datetime
import os

class TranslatorCrew:
    """Crew for translating messages between different domains"""
    
    def __init__(self):
        self.llm_model = os.getenv('LLM_MODEL', 'claude-3-5-sonnet-20241022')
    
    def create_agent(self):
        return Agent(
            role='Marketing Translation Specialist',
            goal="Transform marketing campaign messages into actionable worker tasks",
            backstory="""Expert in marketing operations with deep understanding of 
                        campaign execution and worker task management.""",
            verbose=True,
            llm=LLM(
                model=self.llm_model,
                temperature=0.2
            ),
        )
    
    def create_task(self, agent: Agent, message_data: dict):
        worker_names = message_data.get('worker_names', [])
        input_data = message_data.get('input_data', {})
        
        return Task(
            description=f"""
            Original Message Data:
            {input_data}
            
            Workers to generate tasks for:
            {worker_names}
            
            Transform this message into worker tasks with the following structure:
            {{
                "message": "<task description>",
                "type": "<worker type>",
                "task_id": "<unique task id>",
                "timestamp": "<ISO format timestamp>"
            }}
            
            Generate one task per worker name provided in the worker list.
            Each task's "type" should match exactly with one of the worker names.
            """,
            agent=agent,
            expected_output='JSON formatted worker tasks',
        )
    
    def process(self, message_data: dict) -> list:
        """Process the message and return worker tasks"""
        agent = self.create_agent()
        task = self.create_task(agent, message_data)
        
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff()
        return result.raw 