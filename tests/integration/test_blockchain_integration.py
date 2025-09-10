"""
Integration tests for blockchain components.
"""

import pytest
import asyncio
from agents.infrastructure_crew.blockchain.consensus import ConsensusManager, ConsensusType
from agents.infrastructure_crew.blockchain.transaction import TransactionManager
from agents.infrastructure_crew.blockchain.smart_contract import (
    SmartContract,
    SmartContractInterface,
    ContractStatus
)


@pytest.mark.asyncio
async def test_consensus_transaction_integration():
    """Test integration between consensus and transaction managers."""
    consensus = ConsensusManager(quorum_size=2, timeout_seconds=5.0)
    tx_manager = TransactionManager(required_confirmations=2)
    
    # Create a transaction
    tx = await tx_manager.create_transaction(
        sender_id="agent_1",
        receiver_id="agent_2",
        transaction_type="task_assignment",
        data={"task_id": "task_123"}
    )
    
    # Propose transaction for consensus
    proposal = await consensus.propose(
        proposer_id="agent_1",
        data={
            "transaction_id": tx.transaction_id,
            "action": "confirm_transaction"
        }
    )
    
    # Agents vote on the transaction
    await consensus.vote(proposal.proposal_id, "agent_2", approve=True)
    await consensus.vote(proposal.proposal_id, "agent_3", approve=True)
    
    # Check consensus
    assert await consensus.check_consensus(proposal.proposal_id)
    
    # Confirm transaction after consensus
    await tx_manager.confirm_transaction(tx.transaction_id)
    await tx_manager.confirm_transaction(tx.transaction_id)
    
    # Verify transaction is confirmed
    confirmed_tx = await tx_manager.get_transaction(tx.transaction_id)
    assert confirmed_tx.confirmations == 2


@pytest.mark.asyncio
async def test_smart_contract_with_consensus():
    """Test smart contract execution with consensus."""
    
    class TaskAllocationContract(SmartContract):
        async def allocate_task(self, task_id: str, agent_id: str):
            self.state["allocations"] = self.state.get("allocations", {})
            self.state["allocations"][task_id] = agent_id
            await self.emit_event("TaskAllocated", {
                "task_id": task_id,
                "agent_id": agent_id
            })
            return {"success": True, "task_id": task_id, "agent_id": agent_id}
    
    # Initialize components
    consensus = ConsensusManager(quorum_size=2)
    contract_interface = SmartContractInterface()
    
    # Deploy contract
    contract = TaskAllocationContract(
        contract_id="task_allocation_001",
        owner_id="orchestrator"
    )
    await contract_interface.deploy_contract(contract)
    
    # Propose task allocation
    proposal = await consensus.propose(
        proposer_id="orchestrator",
        data={
            "contract_id": "task_allocation_001",
            "function": "allocate_task",
            "args": {"task_id": "task_456", "agent_id": "worker_1"}
        }
    )
    
    # Vote on proposal
    await consensus.vote(proposal.proposal_id, "agent_1", approve=True)
    await consensus.vote(proposal.proposal_id, "agent_2", approve=True)
    
    # Execute contract after consensus
    if await consensus.check_consensus(proposal.proposal_id):
        result = await contract_interface.execute_contract(
            "task_allocation_001",
            "allocate_task",
            task_id="task_456",
            agent_id="worker_1"
        )
        
        assert result["success"] is True
        assert result["task_id"] == "task_456"
        
        # Verify event was emitted
        events = await contract_interface.get_contract_events("task_allocation_001")
        assert len(events) >= 1  # At least activation + allocation events


@pytest.mark.asyncio
async def test_multi_agent_transaction_workflow():
    """Test complete workflow with multiple agents and transactions."""
    tx_manager = TransactionManager(required_confirmations=3)
    consensus = ConsensusManager(quorum_size=3)
    
    agents = ["agent_1", "agent_2", "agent_3", "agent_4"]
    
    # Create multiple transactions
    transactions = []
    for i, agent in enumerate(agents[:3]):
        tx = await tx_manager.create_transaction(
            sender_id=agent,
            receiver_id=agents[i + 1],
            transaction_type="data_transfer",
            data={"data_id": f"data_{i}"}
        )
        transactions.append(tx)
    
    # Propose batch confirmation
    proposal = await consensus.propose(
        proposer_id="coordinator",
        data={
            "action": "batch_confirm",
            "transaction_ids": [tx.transaction_id for tx in transactions]
        }
    )
    
    # All agents vote
    for agent in agents[:3]:
        await consensus.vote(proposal.proposal_id, agent, approve=True)
    
    # Verify consensus reached
    assert await consensus.check_consensus(proposal.proposal_id)
    
    # Confirm all transactions
    for tx in transactions:
        for _ in range(3):
            await tx_manager.confirm_transaction(tx.transaction_id)
    
    # Verify all transactions confirmed
    for tx in transactions:
        confirmed_tx = await tx_manager.get_transaction(tx.transaction_id)
        assert confirmed_tx.confirmations >= 3


@pytest.mark.asyncio
async def test_smart_contract_event_listeners():
    """Test smart contract event listener functionality."""
    
    class EventEmittingContract(SmartContract):
        async def trigger_event(self, event_name: str, data: dict):
            await self.emit_event(event_name, data)
            return {"emitted": True}
    
    contract_interface = SmartContractInterface()
    contract = EventEmittingContract(
        contract_id="event_test_001",
        owner_id="tester"
    )
    
    # Track received events
    received_events = []
    
    async def event_handler(event):
        received_events.append(event)
    
    # Register listener
    contract.on_event("TestEvent", event_handler)
    
    # Deploy and activate
    await contract_interface.deploy_contract(contract)
    
    # Trigger event
    await contract_interface.execute_contract(
        "event_test_001",
        "trigger_event",
        event_name="TestEvent",
        data={"message": "Hello, World!"}
    )
    
    # Verify event was received
    await asyncio.sleep(0.1)  # Allow async processing
    assert len(received_events) >= 1
    assert any(e.event_name == "TestEvent" for e in received_events)


@pytest.mark.asyncio
async def test_transaction_history_and_filtering():
    """Test transaction history and filtering capabilities."""
    tx_manager = TransactionManager()
    
    # Create various transactions
    agent_1_txs = []
    for i in range(5):
        tx = await tx_manager.create_transaction(
            sender_id="agent_1",
            receiver_id=f"agent_{i+2}",
            transaction_type="task_assignment",
            data={"task_id": f"task_{i}"}
        )
        agent_1_txs.append(tx)
        
        # Confirm some transactions
        if i % 2 == 0:
            for _ in range(3):
                await tx_manager.confirm_transaction(tx.transaction_id)
    
    # Get agent history
    history = await tx_manager.get_transaction_history("agent_1", limit=10)
    assert len(history) == 5
    
    # Get pending transactions
    pending = await tx_manager.get_pending_transactions()
    assert len(pending) > 0
    
    # Get transactions by agent
    agent_txs = await tx_manager.get_transactions_by_agent(
        "agent_1",
        include_sender=True,
        include_receiver=False
    )
    assert len(agent_txs) == 5


@pytest.mark.asyncio
async def test_consensus_timeout_handling():
    """Test consensus timeout scenarios."""
    consensus = ConsensusManager(quorum_size=5, timeout_seconds=1.0)
    
    # Create proposal
    proposal = await consensus.propose(
        proposer_id="agent_1",
        data={"action": "test"}
    )
    
    # Only partial votes (not enough for quorum)
    await consensus.vote(proposal.proposal_id, "agent_2", approve=True)
    await consensus.vote(proposal.proposal_id, "agent_3", approve=True)
    
    # Wait for consensus with timeout
    result = await consensus.wait_for_consensus(proposal.proposal_id, timeout=1.0)
    
    # Should timeout
    assert result is False
    
    # Verify vote count
    vote_count = await consensus.get_vote_count(proposal.proposal_id)
    assert vote_count == 2


@pytest.mark.asyncio
async def test_contract_lifecycle():
    """Test complete smart contract lifecycle."""
    
    class LifecycleContract(SmartContract):
        async def do_work(self):
            return {"status": "work_done"}
    
    interface = SmartContractInterface()
    contract = LifecycleContract(
        contract_id="lifecycle_001",
        owner_id="owner_1"
    )
    
    # Deploy (automatically activates)
    await interface.deploy_contract(contract)
    assert contract.status == ContractStatus.ACTIVE
    
    # Execute function
    result = await interface.execute_contract("lifecycle_001", "do_work")
    assert result["status"] == "work_done"
    
    # Pause contract
    await interface.pause_contract("lifecycle_001")
    assert contract.status == ContractStatus.PAUSED
    
    # Try to execute while paused (should fail)
    with pytest.raises(ValueError):
        await interface.execute_contract("lifecycle_001", "do_work")
    
    # Terminate contract
    await interface.terminate_contract("lifecycle_001")
    assert contract.status == ContractStatus.TERMINATED
