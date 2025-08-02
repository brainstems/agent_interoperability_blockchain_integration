"""
Consensus mechanisms for distributed agent coordination.
"""

import asyncio
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
import hashlib
import json


class ConsensusType(Enum):
    """Types of consensus mechanisms supported."""
    PROOF_OF_WORK = "pow"
    PROOF_OF_STAKE = "pos"
    PRACTICAL_BYZANTINE_FAULT_TOLERANCE = "pbft"
    RAFT = "raft"


@dataclass
class ConsensusProposal:
    """Represents a proposal for consensus."""
    proposal_id: str
    proposer_id: str
    data: Dict[str, Any]
    timestamp: float
    signature: Optional[str] = None


class ConsensusManager:
    """
    Manages consensus protocols for agent coordination.
    
    Provides mechanisms for agents to reach agreement on shared state,
    task allocation, and decision-making in a distributed environment.
    """
    
    def __init__(
        self,
        consensus_type: ConsensusType = ConsensusType.RAFT,
        quorum_size: int = 3,
        timeout_seconds: float = 30.0
    ):
        """
        Initialize the consensus manager.
        
        Args:
            consensus_type: The consensus mechanism to use
            quorum_size: Minimum number of nodes required for consensus
            timeout_seconds: Timeout for consensus operations
        """
        self.consensus_type = consensus_type
        self.quorum_size = quorum_size
        self.timeout_seconds = timeout_seconds
        self.proposals: Dict[str, ConsensusProposal] = {}
        self.votes: Dict[str, List[str]] = {}  # proposal_id -> list of voter_ids
        
    async def propose(
        self,
        proposer_id: str,
        data: Dict[str, Any]
    ) -> ConsensusProposal:
        """
        Submit a proposal for consensus.
        
        Args:
            proposer_id: ID of the proposing agent
            data: Data to reach consensus on
            
        Returns:
            The created consensus proposal
        """
        import time
        
        proposal_id = self._generate_proposal_id(proposer_id, data, time.time())
        proposal = ConsensusProposal(
            proposal_id=proposal_id,
            proposer_id=proposer_id,
            data=data,
            timestamp=time.time()
        )
        
        self.proposals[proposal_id] = proposal
        self.votes[proposal_id] = []
        
        return proposal
    
    async def vote(
        self,
        proposal_id: str,
        voter_id: str,
        approve: bool = True
    ) -> bool:
        """
        Cast a vote on a proposal.
        
        Args:
            proposal_id: ID of the proposal to vote on
            voter_id: ID of the voting agent
            approve: Whether to approve the proposal
            
        Returns:
            True if vote was recorded successfully
        """
        if proposal_id not in self.proposals:
            return False
            
        if approve and voter_id not in self.votes[proposal_id]:
            self.votes[proposal_id].append(voter_id)
            
        return True
    
    async def check_consensus(self, proposal_id: str) -> bool:
        """
        Check if consensus has been reached for a proposal.
        
        Args:
            proposal_id: ID of the proposal to check
            
        Returns:
            True if consensus has been reached
        """
        if proposal_id not in self.proposals:
            return False
            
        vote_count = len(self.votes.get(proposal_id, []))
        return vote_count >= self.quorum_size
    
    async def wait_for_consensus(
        self,
        proposal_id: str,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Wait for consensus to be reached on a proposal.
        
        Args:
            proposal_id: ID of the proposal
            timeout: Optional timeout override
            
        Returns:
            True if consensus was reached within timeout
        """
        timeout = timeout or self.timeout_seconds
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            if await self.check_consensus(proposal_id):
                return True
            await asyncio.sleep(0.1)
            
        return False
    
    def _generate_proposal_id(
        self,
        proposer_id: str,
        data: Dict[str, Any],
        timestamp: float
    ) -> str:
        """Generate a unique proposal ID."""
        content = f"{proposer_id}:{json.dumps(data, sort_keys=True)}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def get_proposal(self, proposal_id: str) -> Optional[ConsensusProposal]:
        """Retrieve a proposal by ID."""
        return self.proposals.get(proposal_id)
    
    async def get_vote_count(self, proposal_id: str) -> int:
        """Get the current vote count for a proposal."""
        return len(self.votes.get(proposal_id, []))
