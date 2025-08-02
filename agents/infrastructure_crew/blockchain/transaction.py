"""
Transaction management for blockchain-based agent coordination.
"""

import hashlib
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class TransactionStatus(Enum):
    """Status of a blockchain transaction."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass
class Transaction:
    """Represents a blockchain transaction for agent coordination."""
    transaction_id: str
    sender_id: str
    receiver_id: str
    transaction_type: str
    data: Dict[str, Any]
    timestamp: float
    status: TransactionStatus = TransactionStatus.PENDING
    confirmations: int = 0
    signature: Optional[str] = None
    block_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            "transaction_id": self.transaction_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "transaction_type": self.transaction_type,
            "data": self.data,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "confirmations": self.confirmations,
            "signature": self.signature,
            "block_hash": self.block_hash
        }


class TransactionManager:
    """
    Manages blockchain transactions for agent interactions.
    
    Handles creation, validation, and tracking of transactions between agents,
    ensuring secure and verifiable agent-to-agent communication.
    """
    
    def __init__(self, required_confirmations: int = 3):
        """
        Initialize the transaction manager.
        
        Args:
            required_confirmations: Number of confirmations required for finality
        """
        self.required_confirmations = required_confirmations
        self.transactions: Dict[str, Transaction] = {}
        self.pending_transactions: List[str] = []
        
    async def create_transaction(
        self,
        sender_id: str,
        receiver_id: str,
        transaction_type: str,
        data: Dict[str, Any]
    ) -> Transaction:
        """
        Create a new transaction.
        
        Args:
            sender_id: ID of the sending agent
            receiver_id: ID of the receiving agent
            transaction_type: Type of transaction (e.g., 'task_assignment', 'data_transfer')
            data: Transaction payload
            
        Returns:
            The created transaction
        """
        transaction_id = self._generate_transaction_id(
            sender_id, receiver_id, transaction_type, data, time.time()
        )
        
        transaction = Transaction(
            transaction_id=transaction_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            transaction_type=transaction_type,
            data=data,
            timestamp=time.time()
        )
        
        self.transactions[transaction_id] = transaction
        self.pending_transactions.append(transaction_id)
        
        return transaction
    
    async def confirm_transaction(
        self,
        transaction_id: str,
        block_hash: Optional[str] = None
    ) -> bool:
        """
        Confirm a transaction.
        
        Args:
            transaction_id: ID of the transaction to confirm
            block_hash: Optional hash of the block containing the transaction
            
        Returns:
            True if confirmation was successful
        """
        if transaction_id not in self.transactions:
            return False
            
        transaction = self.transactions[transaction_id]
        transaction.confirmations += 1
        
        if block_hash:
            transaction.block_hash = block_hash
            
        if transaction.confirmations >= self.required_confirmations:
            transaction.status = TransactionStatus.CONFIRMED
            if transaction_id in self.pending_transactions:
                self.pending_transactions.remove(transaction_id)
                
        return True
    
    async def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Retrieve a transaction by ID."""
        return self.transactions.get(transaction_id)
    
    async def get_pending_transactions(self) -> List[Transaction]:
        """Get all pending transactions."""
        return [
            self.transactions[tx_id]
            for tx_id in self.pending_transactions
            if tx_id in self.transactions
        ]
    
    async def get_transactions_by_agent(
        self,
        agent_id: str,
        include_sender: bool = True,
        include_receiver: bool = True
    ) -> List[Transaction]:
        """
        Get all transactions involving a specific agent.
        
        Args:
            agent_id: ID of the agent
            include_sender: Include transactions where agent is sender
            include_receiver: Include transactions where agent is receiver
            
        Returns:
            List of matching transactions
        """
        transactions = []
        
        for transaction in self.transactions.values():
            if include_sender and transaction.sender_id == agent_id:
                transactions.append(transaction)
            elif include_receiver and transaction.receiver_id == agent_id:
                transactions.append(transaction)
                
        return transactions
    
    async def reject_transaction(self, transaction_id: str, reason: str = "") -> bool:
        """
        Reject a transaction.
        
        Args:
            transaction_id: ID of the transaction to reject
            reason: Optional reason for rejection
            
        Returns:
            True if rejection was successful
        """
        if transaction_id not in self.transactions:
            return False
            
        transaction = self.transactions[transaction_id]
        transaction.status = TransactionStatus.REJECTED
        
        if transaction_id in self.pending_transactions:
            self.pending_transactions.remove(transaction_id)
            
        return True
    
    def _generate_transaction_id(
        self,
        sender_id: str,
        receiver_id: str,
        transaction_type: str,
        data: Dict[str, Any],
        timestamp: float
    ) -> str:
        """Generate a unique transaction ID."""
        content = f"{sender_id}:{receiver_id}:{transaction_type}:{json.dumps(data, sort_keys=True)}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def get_transaction_history(
        self,
        agent_id: str,
        limit: Optional[int] = None
    ) -> List[Transaction]:
        """
        Get transaction history for an agent.
        
        Args:
            agent_id: ID of the agent
            limit: Optional limit on number of transactions to return
            
        Returns:
            List of transactions, sorted by timestamp (newest first)
        """
        transactions = await self.get_transactions_by_agent(agent_id)
        transactions.sort(key=lambda tx: tx.timestamp, reverse=True)
        
        if limit:
            transactions = transactions[:limit]
            
        return transactions
