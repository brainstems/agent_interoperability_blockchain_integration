"""
Blockchain integration module for agent interoperability.

This module provides blockchain-based coordination and consensus mechanisms
for multi-agent systems.
"""

from .consensus import ConsensusManager
from .transaction import TransactionManager
from .smart_contract import SmartContractInterface

__all__ = [
    "ConsensusManager",
    "TransactionManager",
    "SmartContractInterface",
]
