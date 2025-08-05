"""
Unit tests for blockchain consensus mechanisms.
"""

import pytest
import asyncio
from agents.infrastructure_crew.blockchain.consensus import (
    ConsensusManager,
    ConsensusType,
    ConsensusProposal
)


@pytest.mark.asyncio
async def test_consensus_manager_initialization():
    """Test consensus manager initialization."""
    manager = ConsensusManager(
        consensus_type=ConsensusType.RAFT,
        quorum_size=3,
        timeout_seconds=30.0
    )
    
    assert manager.consensus_type == ConsensusType.RAFT
    assert manager.quorum_size == 3
    assert manager.timeout_seconds == 30.0
    assert len(manager.proposals) == 0
    assert len(manager.votes) == 0


@pytest.mark.asyncio
async def test_create_proposal():
    """Test creating a consensus proposal."""
    manager = ConsensusManager(quorum_size=2)
    
    proposal = await manager.propose(
        proposer_id="agent_1",
        data={"action": "allocate_task", "task_id": "task_123"}
    )
    
    assert isinstance(proposal, ConsensusProposal)
    assert proposal.proposer_id == "agent_1"
    assert proposal.data["action"] == "allocate_task"
    assert proposal.proposal_id in manager.proposals


@pytest.mark.asyncio
async def test_voting_on_proposal():
    """Test voting on a proposal."""
    manager = ConsensusManager(quorum_size=2)
    
    proposal = await manager.propose(
        proposer_id="agent_1",
        data={"action": "test"}
    )
    
    # Cast votes
    assert await manager.vote(proposal.proposal_id, "agent_2", approve=True)
    assert await manager.vote(proposal.proposal_id, "agent_3", approve=True)
    
    # Check vote count
    vote_count = await manager.get_vote_count(proposal.proposal_id)
    assert vote_count == 2


@pytest.mark.asyncio
async def test_consensus_reached():
    """Test checking if consensus is reached."""
    manager = ConsensusManager(quorum_size=2)
    
    proposal = await manager.propose(
        proposer_id="agent_1",
        data={"action": "test"}
    )
    
    # Before quorum
    assert not await manager.check_consensus(proposal.proposal_id)
    
    # Cast votes to reach quorum
    await manager.vote(proposal.proposal_id, "agent_2", approve=True)
    await manager.vote(proposal.proposal_id, "agent_3", approve=True)
    
    # After quorum
    assert await manager.check_consensus(proposal.proposal_id)


@pytest.mark.asyncio
async def test_wait_for_consensus():
    """Test waiting for consensus to be reached."""
    manager = ConsensusManager(quorum_size=2, timeout_seconds=2.0)
    
    proposal = await manager.propose(
        proposer_id="agent_1",
        data={"action": "test"}
    )
    
    # Start voting in background
    async def vote_later():
        await asyncio.sleep(0.5)
        await manager.vote(proposal.proposal_id, "agent_2", approve=True)
        await manager.vote(proposal.proposal_id, "agent_3", approve=True)
    
    asyncio.create_task(vote_later())
    
    # Wait for consensus
    result = await manager.wait_for_consensus(proposal.proposal_id, timeout=2.0)
    assert result is True


@pytest.mark.asyncio
async def test_consensus_timeout():
    """Test consensus timeout."""
    manager = ConsensusManager(quorum_size=3, timeout_seconds=0.5)
    
    proposal = await manager.propose(
        proposer_id="agent_1",
        data={"action": "test"}
    )
    
    # Only one vote, not enough for quorum
    await manager.vote(proposal.proposal_id, "agent_2", approve=True)
    
    # Should timeout
    result = await manager.wait_for_consensus(proposal.proposal_id)
    assert result is False


@pytest.mark.asyncio
async def test_get_proposal():
    """Test retrieving a proposal."""
    manager = ConsensusManager()
    
    proposal = await manager.propose(
        proposer_id="agent_1",
        data={"action": "test"}
    )
    
    retrieved = await manager.get_proposal(proposal.proposal_id)
    assert retrieved is not None
    assert retrieved.proposal_id == proposal.proposal_id
    assert retrieved.proposer_id == "agent_1"
