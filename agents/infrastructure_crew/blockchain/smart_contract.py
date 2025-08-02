"""
Smart contract interface for agent coordination and automation.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio


class ContractStatus(Enum):
    """Status of a smart contract."""
    DEPLOYED = "deployed"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"


@dataclass
class ContractEvent:
    """Represents an event emitted by a smart contract."""
    event_name: str
    contract_id: str
    data: Dict[str, Any]
    timestamp: float
    block_number: Optional[int] = None


class SmartContract:
    """
    Base class for smart contracts in the agent ecosystem.
    
    Smart contracts define rules and automation for agent interactions,
    task execution, and resource allocation.
    """
    
    def __init__(self, contract_id: str, owner_id: str):
        """
        Initialize a smart contract.
        
        Args:
            contract_id: Unique identifier for the contract
            owner_id: ID of the contract owner/deployer
        """
        self.contract_id = contract_id
        self.owner_id = owner_id
        self.status = ContractStatus.DEPLOYED
        self.state: Dict[str, Any] = {}
        self.events: List[ContractEvent] = []
        self.event_listeners: Dict[str, List[Callable]] = {}
        
    async def execute(self, function_name: str, **kwargs) -> Any:
        """
        Execute a contract function.
        
        Args:
            function_name: Name of the function to execute
            **kwargs: Function arguments
            
        Returns:
            Result of the function execution
        """
        if self.status != ContractStatus.ACTIVE:
            raise ValueError(f"Contract is not active (status: {self.status})")
            
        if not hasattr(self, function_name):
            raise ValueError(f"Function '{function_name}' not found in contract")
            
        func = getattr(self, function_name)
        return await func(**kwargs)
    
    async def emit_event(self, event_name: str, data: Dict[str, Any]):
        """
        Emit an event from the contract.
        
        Args:
            event_name: Name of the event
            data: Event data
        """
        import time
        
        event = ContractEvent(
            event_name=event_name,
            contract_id=self.contract_id,
            data=data,
            timestamp=time.time()
        )
        
        self.events.append(event)
        
        # Notify listeners
        if event_name in self.event_listeners:
            for listener in self.event_listeners[event_name]:
                await listener(event)
    
    def on_event(self, event_name: str, callback: Callable):
        """
        Register an event listener.
        
        Args:
            event_name: Name of the event to listen for
            callback: Callback function to execute when event is emitted
        """
        if event_name not in self.event_listeners:
            self.event_listeners[event_name] = []
        self.event_listeners[event_name].append(callback)
    
    async def activate(self):
        """Activate the contract."""
        self.status = ContractStatus.ACTIVE
        await self.emit_event("ContractActivated", {"contract_id": self.contract_id})
    
    async def pause(self):
        """Pause the contract."""
        self.status = ContractStatus.PAUSED
        await self.emit_event("ContractPaused", {"contract_id": self.contract_id})
    
    async def terminate(self):
        """Terminate the contract."""
        self.status = ContractStatus.TERMINATED
        await self.emit_event("ContractTerminated", {"contract_id": self.contract_id})


class SmartContractInterface:
    """
    Interface for managing and interacting with smart contracts.
    
    Provides deployment, execution, and monitoring capabilities for
    smart contracts in the agent ecosystem.
    """
    
    def __init__(self):
        """Initialize the smart contract interface."""
        self.contracts: Dict[str, SmartContract] = {}
        
    async def deploy_contract(
        self,
        contract: SmartContract
    ) -> str:
        """
        Deploy a smart contract.
        
        Args:
            contract: The contract to deploy
            
        Returns:
            The contract ID
        """
        self.contracts[contract.contract_id] = contract
        await contract.activate()
        return contract.contract_id
    
    async def execute_contract(
        self,
        contract_id: str,
        function_name: str,
        **kwargs
    ) -> Any:
        """
        Execute a function on a deployed contract.
        
        Args:
            contract_id: ID of the contract
            function_name: Name of the function to execute
            **kwargs: Function arguments
            
        Returns:
            Result of the function execution
        """
        if contract_id not in self.contracts:
            raise ValueError(f"Contract {contract_id} not found")
            
        contract = self.contracts[contract_id]
        return await contract.execute(function_name, **kwargs)
    
    async def get_contract(self, contract_id: str) -> Optional[SmartContract]:
        """Retrieve a contract by ID."""
        return self.contracts.get(contract_id)
    
    async def get_contract_events(
        self,
        contract_id: str,
        event_name: Optional[str] = None
    ) -> List[ContractEvent]:
        """
        Get events emitted by a contract.
        
        Args:
            contract_id: ID of the contract
            event_name: Optional filter by event name
            
        Returns:
            List of contract events
        """
        if contract_id not in self.contracts:
            return []
            
        contract = self.contracts[contract_id]
        events = contract.events
        
        if event_name:
            events = [e for e in events if e.event_name == event_name]
            
        return events
    
    async def pause_contract(self, contract_id: str) -> bool:
        """Pause a contract."""
        if contract_id not in self.contracts:
            return False
            
        await self.contracts[contract_id].pause()
        return True
    
    async def terminate_contract(self, contract_id: str) -> bool:
        """Terminate a contract."""
        if contract_id not in self.contracts:
            return False
            
        await self.contracts[contract_id].terminate()
        return True
    
    async def list_contracts(
        self,
        owner_id: Optional[str] = None,
        status: Optional[ContractStatus] = None
    ) -> List[SmartContract]:
        """
        List deployed contracts.
        
        Args:
            owner_id: Optional filter by owner
            status: Optional filter by status
            
        Returns:
            List of matching contracts
        """
        contracts = list(self.contracts.values())
        
        if owner_id:
            contracts = [c for c in contracts if c.owner_id == owner_id]
            
        if status:
            contracts = [c for c in contracts if c.status == status]
            
        return contracts
