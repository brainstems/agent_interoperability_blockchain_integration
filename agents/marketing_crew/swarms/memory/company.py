from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import os
import glob
from crewai import Agent, Crew, Process, Task
from .agent import Memory, LLMInteraction, EntityState


class CompanyMemoryAgent:

    def __init__(
        self,
        company_id: str,
        storage_dir: str="company_memories",
        memory_threshold: float=0.8  # Higher threshold for company-level memories
    ):
        self.company_id = company_id
        self.storage_dir = storage_dir
        self.memory_threshold = memory_threshold
        self.company_memory: List[Memory] = []
        os.makedirs(storage_dir, exist_ok=True)
        self._load_existing_memories()

    def _create_evaluator_agent(self) -> Agent:
        return Agent(
            role='Corporate Memory Evaluator',
            goal="Evaluate strategic importance of information for company-wide knowledge",
            backstory="""Senior Knowledge Management Executive with:
            - Deep understanding of organizational learning
            - Expertise in identifying strategically valuable information
            - Strong business acumen and market awareness
            - Focus on long-term company value and competitive advantage
            - Experience in cross-departmental knowledge synthesis""",
            verbose=True
        )

    def evaluate_memory_importance(
        self,
        input_data: Dict[str, Any],
        outcome: Dict[str, Any]
    ) -> float:
        """Use CrewAI to evaluate if a memory should be stored at company level."""
        agent = self._create_evaluator_agent()
        
        task = Task(
            description=f"""
            Evaluate the company-wide importance of this information on a scale of 0 to 1.
            Consider factors like:
            - Strategic impact on company objectives
            - Cross-departmental relevance
            - Market or competitive insights
            - Innovation potential
            - Risk management implications
            - Financial impact
            - Organizational learning value
            - Regulatory or compliance significance

            Input: {json.dumps(input_data, indent=2)}
            Outcome: {json.dumps(outcome, indent=2)}

            Return only a float value between 0 and 1.
            """,
            agent=agent
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )

        result = crew.kickoff()
        importance_score = float(str(result).strip())
        return min(max(importance_score, 0.0), 1.0)

    def create_memory(
        self,
        memory_id: str,
        input_data: Dict[str, Any],
        outcome: Dict[str, Any],
        company_state: Dict[str, Any],
        entities: List[EntityState],
        source_type: str="direct"  # direct, swarm, or department
    ) -> Optional[Memory]:
        """Create a new company-level memory if it passes the importance threshold."""
        
        importance_score = self.evaluate_memory_importance(input_data, outcome)
        
        if importance_score >= self.memory_threshold:
            llm_interaction = LLMInteraction(
                context=input_data,
                prompt="",
                output=outcome
            )
            
            memory = Memory(
                memory_id=memory_id,
                memory_level="company",
                llm_interaction=llm_interaction,
                agent_state={
                    **company_state,
                    "source_type": source_type,
                    "importance_score": importance_score
                },
                entities=entities
            )
            
            self.company_memory.append(memory)
            self._save_to_file(memory)
            return memory
        
        return None

    def _save_to_file(self, memory: Memory) -> None:
        filename = f"{self.storage_dir}/{self.company_id}_{memory.memory_id}.json"
        with open(filename, 'w') as f:
            json.dump(memory.to_dict(), f, indent=2)

    def _load_existing_memories(self) -> None:
        """Load all existing company memories from the file system."""
        pattern = f"{self.storage_dir}/{self.company_id}_*.json"
        for filename in glob.glob(pattern):
            with open(filename, 'r') as f:
                memory_dict = json.load(f)
                llm_interaction = LLMInteraction(
                    memory_dict['context'],
                    memory_dict['prompt'],
                    memory_dict['output']
                )
                entities = [
                    EntityState(**entity_dict)
                    for entity_dict in memory_dict['entities']
                ]
                memory = Memory(
                    memory_id=memory_dict['memory_id'],
                    memory_level=memory_dict['memory_level'],
                    llm_interaction=llm_interaction,
                    agent_state=memory_dict['agent_state'],
                    entities=entities,
                    timestamp=memory_dict['timestamp']
                )
                self.company_memory.append(memory)

    def get_all_memories(self) -> List[Memory]:
        """Return all company memories."""
        return self.company_memory

    def get_memory_by_id(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a specific memory by its ID."""
        for memory in self.company_memory:
            if memory.memory_id == memory_id:
                return memory
        return None

    def get_memories_by_timerange(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Memory]:
        """Retrieve memories within a specific time range."""
        memories = []
        for memory in self.company_memory:
            memory_time = datetime.fromisoformat(memory.timestamp)
            if start_time <= memory_time <= end_time:
                memories.append(memory)
        return memories

    def get_memories_by_source(self, source_type: str) -> List[Memory]:
        """Retrieve memories by their source type (direct, swarm, or department)."""
        memories = []
        for memory in self.company_memory:
            if memory.agent_state.get("source_type") == source_type:
                memories.append(memory)
        return memories

    def get_memories_by_importance_threshold(
        self,
        min_importance: float=0.0,
        max_importance: float=1.0
    ) -> List[Memory]:
        """Retrieve memories within a specific importance score range."""
        memories = []
        for memory in self.company_memory:
            importance_score = memory.agent_state.get("importance_score", 0.0)
            if min_importance <= importance_score <= max_importance:
                memories.append(memory)
        return memories
