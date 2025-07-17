from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import os
import glob
from crewai import Agent, Crew, Process, Task
from .agent import Memory, LLMInteraction, EntityState


class SwarmMemoryAgent:

    def __init__(
        self,
        swarm_id: str,
        storage_dir: str="swarm_memories",
        memory_threshold: float=0.7  # Threshold for memory importance
    ):
        self.swarm_id = swarm_id
        self.storage_dir = storage_dir
        self.memory_threshold = memory_threshold
        self.swarm_memory: List[Memory] = []
        os.makedirs(storage_dir, exist_ok=True)
        self._load_existing_memories()

    def _create_evaluator_agent(self) -> Agent:
        return Agent(
            role='Memory Evaluator',
            goal="Accurately evaluate the importance of memories for swarm intelligence",
            backstory="""Expert at evaluating information importance with:
            - Deep understanding of swarm intelligence
            - Strong analytical capabilities
            - Ability to identify critical patterns and insights
            - Focus on long-term strategic value""",
            verbose=True
        )

    def evaluate_memory_importance(
        self,
        input_data: Dict[str, Any],
        outcome: Dict[str, Any]
    ) -> float:
        """Use CrewAI to evaluate if a memory should be stored based on its importance."""
        agent = self._create_evaluator_agent()
        
        task = Task(
            description=f"""
            Evaluate the importance of this interaction for the swarm's memory on a scale of 0 to 1.
            Consider factors like:
            - Novel information or patterns
            - Critical decisions or outcomes
            - Unique interactions or failures
            - Strategic value for future operations

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
        return min(max(importance_score, 0.0), 1.0)  # Ensure value is between 0 and 1

    def create_memory(
        self,
        memory_id: str,
        input_data: Dict[str, Any],
        outcome: Dict[str, Any],
        agent_state: Dict[str, Any],
        entities: List[EntityState],
    ) -> Optional[Memory]:
        """Create a new memory if it passes the importance threshold."""
        
        importance_score = self.evaluate_memory_importance(input_data, outcome)
        
        if importance_score >= self.memory_threshold:
            llm_interaction = LLMInteraction(
                context=input_data,
                prompt="",  # Could store the evaluation prompt here if needed
                output=outcome
            )
            
            memory = Memory(
                memory_id=memory_id,
                memory_level="swarm",
                llm_interaction=llm_interaction,
                agent_state=agent_state,
                entities=entities
            )
            
            self.swarm_memory.append(memory)
            self._save_to_file(memory)
            return memory
        
        return None

    def _save_to_file(self, memory: Memory) -> None:
        filename = f"{self.storage_dir}/{self.swarm_id}_{memory.memory_id}.json"
        with open(filename, 'w') as f:
            json.dump(memory.to_dict(), f, indent=2)

    def _load_existing_memories(self) -> None:
        """Load all existing memories for this swarm from the file system."""
        pattern = f"{self.storage_dir}/{self.swarm_id}_*.json"
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
                self.swarm_memory.append(memory)

    def get_all_memories(self) -> List[Memory]:
        """Return all swarm memories."""
        return self.swarm_memory

    def get_memory_by_id(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a specific memory by its ID."""
        for memory in self.swarm_memory:
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
        for memory in self.swarm_memory:
            memory_time = datetime.fromisoformat(memory.timestamp)
            if start_time <= memory_time <= end_time:
                memories.append(memory)
        return memories
