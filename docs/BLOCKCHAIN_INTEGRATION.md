# Blockchain Integration Guide

## Overview

The Agent Interoperability & Blockchain Integration project provides a comprehensive blockchain layer for secure, decentralized agent coordination. This document outlines the blockchain components and their usage.

## Architecture

### Core Components

1. **Consensus Manager** - Manages distributed consensus protocols
2. **Transaction Manager** - Handles blockchain transactions between agents
3. **Smart Contract Interface** - Deploys and executes smart contracts for automation

## Consensus Manager

The `ConsensusManager` enables agents to reach agreement on shared state, task allocation, and decision-making.

### Supported Consensus Types

- **RAFT** - Leader-based consensus for high availability
- **PBFT** - Practical Byzantine Fault Tolerance for adversarial environments
- **Proof of Work** - Computational proof-based consensus
- **Proof of Stake** - Stake-based consensus mechanism

### Usage Example

```python
from infrastructure_crew.blockchain.consensus import ConsensusManager, ConsensusType

# Initialize consensus manager
consensus = ConsensusManager(
    consensus_type=ConsensusType.RAFT,
    quorum_size=3,
    timeout_seconds=30.0
)

# Create a proposal
proposal = await consensus.propose(
    proposer_id="agent_1",
    data={"action": "allocate_task", "task_id": "task_123"}
)

# Agents vote on the proposal
await consensus.vote(proposal.proposal_id, "agent_2", approve=True)
await consensus.vote(proposal.proposal_id, "agent_3", approve=True)

# Check if consensus is reached
if await consensus.check_consensus(proposal.proposal_id):
    print("Consensus reached!")
```

## Transaction Manager

The `TransactionManager` provides secure, verifiable transactions between agents.

### Transaction Types

- **task_assignment** - Assign tasks between agents
- **data_transfer** - Transfer data securely
- **resource_allocation** - Allocate resources
- **payment** - Handle payments and rewards

### Usage Example

```python
from infrastructure_crew.blockchain.transaction import TransactionManager

# Initialize transaction manager
tx_manager = TransactionManager(required_confirmations=3)

# Create a transaction
transaction = await tx_manager.create_transaction(
    sender_id="agent_1",
    receiver_id="agent_2",
    transaction_type="task_assignment",
    data={"task_id": "task_123", "priority": "high"}
)

# Confirm transaction
await tx_manager.confirm_transaction(
    transaction.transaction_id,
    block_hash="0x1234..."
)

# Get transaction history
history = await tx_manager.get_transaction_history("agent_1", limit=10)
```

## Smart Contract Interface

Smart contracts enable automated execution of agent coordination logic.

### Creating a Smart Contract

```python
from infrastructure_crew.blockchain.smart_contract import SmartContract, SmartContractInterface

class TaskAllocationContract(SmartContract):
    """Contract for automated task allocation."""
    
    async def allocate_task(self, task_id: str, agent_id: str):
        """Allocate a task to an agent."""
        self.state["allocations"] = self.state.get("allocations", {})
        self.state["allocations"][task_id] = agent_id
        
        await self.emit_event("TaskAllocated", {
            "task_id": task_id,
            "agent_id": agent_id
        })
        
        return {"success": True, "task_id": task_id, "agent_id": agent_id}

# Deploy the contract
interface = SmartContractInterface()
contract = TaskAllocationContract(
    contract_id="task_allocation_v1",
    owner_id="infrastructure_crew"
)

contract_id = await interface.deploy_contract(contract)

# Execute contract function
result = await interface.execute_contract(
    contract_id,
    "allocate_task",
    task_id="task_123",
    agent_id="agent_1"
)
```

## Integration with CrewManager

The blockchain components are automatically initialized in the `CrewManager`:

```python
config = {
    "blockchain_config": {
        "consensus_type": "RAFT",
        "quorum_size": 3,
        "timeout_seconds": 30.0,
        "required_confirmations": 3
    }
}

crew_manager = CrewManager(config)
await crew_manager.initialize()

# Access blockchain components
consensus = crew_manager.consensus_manager
transactions = crew_manager.transaction_manager
contracts = crew_manager.smart_contract_interface
```

## Use Cases

### 1. Distributed Task Allocation

Use consensus to agree on task assignments across multiple agents:

```python
# Propose task allocation
proposal = await consensus.propose(
    proposer_id="orchestrator",
    data={
        "task_id": "task_456",
        "assigned_agent": "worker_3",
        "priority": "high"
    }
)

# Agents vote
for agent_id in ["agent_1", "agent_2", "agent_3"]:
    await consensus.vote(proposal.proposal_id, agent_id, approve=True)

# Wait for consensus
if await consensus.wait_for_consensus(proposal.proposal_id):
    # Create transaction to record allocation
    tx = await transactions.create_transaction(
        sender_id="orchestrator",
        receiver_id="worker_3",
        transaction_type="task_assignment",
        data=proposal.data
    )
```

### 2. Secure Data Exchange

Use transactions to track data transfers between agents:

```python
# Agent 1 sends data to Agent 2
tx = await transactions.create_transaction(
    sender_id="agent_1",
    receiver_id="agent_2",
    transaction_type="data_transfer",
    data={
        "data_type": "analysis_results",
        "payload_hash": "sha256:abc123...",
        "size_bytes": 1024
    }
)

# Confirm after successful transfer
await transactions.confirm_transaction(tx.transaction_id)
```

### 3. Automated Workflows

Deploy smart contracts for complex multi-agent workflows:

```python
class WorkflowContract(SmartContract):
    async def start_workflow(self, workflow_id: str, participants: list):
        self.state["workflows"] = self.state.get("workflows", {})
        self.state["workflows"][workflow_id] = {
            "status": "active",
            "participants": participants,
            "completed_steps": []
        }
        await self.emit_event("WorkflowStarted", {"workflow_id": workflow_id})
    
    async def complete_step(self, workflow_id: str, step_id: str, agent_id: str):
        workflow = self.state["workflows"][workflow_id]
        workflow["completed_steps"].append({
            "step_id": step_id,
            "agent_id": agent_id,
            "timestamp": time.time()
        })
        await self.emit_event("StepCompleted", {
            "workflow_id": workflow_id,
            "step_id": step_id
        })
```

## Security Considerations

1. **Transaction Validation** - All transactions are validated before confirmation
2. **Consensus Quorum** - Requires majority agreement for decisions
3. **Smart Contract Auditing** - Review contract logic before deployment
4. **Access Control** - Implement proper authorization in contracts

## Performance Tuning

- **Quorum Size**: Balance between security and speed (3-5 recommended)
- **Confirmation Requirements**: Higher values increase security but reduce throughput
- **Timeout Settings**: Adjust based on network latency and agent response times

## Future Enhancements

- Integration with public blockchains (Ethereum, Polygon)
- Zero-knowledge proofs for privacy-preserving coordination
- Cross-chain interoperability
- Decentralized identity management for agents
