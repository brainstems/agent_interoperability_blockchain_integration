from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time
import json
import os
from datetime import datetime
import glob


@dataclass
class LLMInteraction:
    context: Dict[str, Any]
    prompt: str
    output: Dict[str, Any]


@dataclass
class EntityState:
    entity_id: str
    entity_type: str
    attributes: Dict[str, Any]
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Memory:
    memory_id: str
    memory_level: str  # personal, swarm, or company
    llm_interaction: LLMInteraction
    agent_state: Dict[str, Any]
    entities: List[EntityState]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "memory_level": self.memory_level,
            "context": self.llm_interaction.context,
            "prompt": self.llm_interaction.prompt,
            "output": self.llm_interaction.output,
            "agent_state": self.agent_state,
            "entities": [entity.__dict__ for entity in self.entities],
            "timestamp": self.timestamp
        }


class Agent:

    def __init__(self, agent_id: str, swarm_id: str, storage_dir: str="memories"):
        self.agent_id = agent_id
        self.swarm_id = swarm_id
        self.personal_memory: List[Memory] = []
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self._load_existing_memories()  # Load memories on initialization
    
    def create_memory(
        self,
        memory_id: str,
        context: Dict[str, Any],
        prompt: str,
        output: Dict[str, Any],
        agent_state: Dict[str, Any],
        entities: List[EntityState],
        memory_level: str="personal"
    ) -> Memory:
        llm_interaction = LLMInteraction(context, prompt, output)
        memory = Memory(memory_id, memory_level, llm_interaction, agent_state, entities)
        self.personal_memory.append(memory)
        self._save_to_file(memory)
        return memory
    
    def _save_to_file(self, memory: Memory) -> None:
        filename = f"{self.storage_dir}/{self.agent_id}_{memory.memory_id}.json"
        with open(filename, 'w') as f:
            json.dump(memory.to_dict(), f, indent=2)
    
    def share_with_swarm(self, memory: Memory) -> Dict:
        return {
            "type": "personal_memory",
            "agent_id": self.agent_id,
            "swarm_id": self.swarm_id,
            "memory": memory.to_dict()
        }

    def _load_existing_memories(self) -> None:
        """Load all existing memories for this agent from the file system."""
        pattern = f"{self.storage_dir}/{self.agent_id}_*.json"
        for filename in glob.glob(pattern):
            with open(filename, 'r') as f:
                memory_dict = json.load(f)
                # Reconstruct Memory object from dict
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
                self.personal_memory.append(memory) 

    def get_all_memories(self) -> List[Memory]:
        """Return all memories for this agent."""
        return self.personal_memory

    def get_memory_by_id(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a specific memory by its ID."""
        for memory in self.personal_memory:
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
        for memory in self.personal_memory:
            memory_time = datetime.fromisoformat(memory.timestamp)
            if start_time <= memory_time <= end_time:
                memories.append(memory)
        return memories
