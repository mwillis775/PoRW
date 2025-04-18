"""
Smart contract models for the PoRW blockchain.

This module defines the data structures for smart contracts, including
contract code, state, and execution context.
"""

import hashlib
import json
import time
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field, validator


class ContractLanguage(str, Enum):
    """Supported smart contract languages."""
    PYTHON = "python"  # Python-based contracts
    WASM = "wasm"      # WebAssembly contracts
    JSON = "json"      # Simple JSON-based contracts


class ContractState(str, Enum):
    """Possible states of a smart contract."""
    PENDING = "pending"    # Contract is pending deployment
    ACTIVE = "active"      # Contract is active and can be executed
    PAUSED = "paused"      # Contract is temporarily paused
    TERMINATED = "terminated"  # Contract has been permanently terminated


class SmartContract(BaseModel):
    """
    Represents a smart contract in the PoRW blockchain.
    
    A smart contract contains code that can be executed in response to
    transactions or other events on the blockchain.
    """
    contract_id: Optional[str] = Field(None, description="Unique identifier for the contract")
    creator: str = Field(..., description="Address of the contract creator")
    name: str = Field(..., description="Human-readable name for the contract")
    description: Optional[str] = Field(None, description="Description of the contract's purpose")
    language: ContractLanguage = Field(..., description="Programming language of the contract")
    code: str = Field(..., description="Source code of the contract")
    abi: Dict[str, Any] = Field(..., description="Application Binary Interface (ABI) defining the contract's functions")
    state: ContractState = Field(ContractState.PENDING, description="Current state of the contract")
    created_at: float = Field(default_factory=time.time, description="Timestamp when the contract was created")
    updated_at: Optional[float] = Field(None, description="Timestamp when the contract was last updated")
    storage: Dict[str, Any] = Field(default_factory=dict, description="Contract's persistent storage")
    balance: float = Field(0.0, ge=0, description="Balance of the contract in PORW tokens")
    version: int = Field(1, description="Version of the contract")
    
    # Automatically generate contract_id if not provided
    @validator('contract_id', pre=True, always=True)
    def set_contract_id(cls, v, values):
        if v is None:
            # Create a stable representation for hashing
            contract_data = {
                "creator": values.get('creator'),
                "name": values.get('name'),
                "language": values.get('language'),
                "code": values.get('code'),
                "created_at": values.get('created_at', time.time())
            }
            contract_string = json.dumps(contract_data, sort_keys=True)
            return hashlib.sha256(contract_string.encode()).hexdigest()
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the contract to a dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SmartContract':
        """Create a contract from a dictionary."""
        return cls(**data)


class ContractTransaction(BaseModel):
    """
    Represents a transaction that interacts with a smart contract.
    
    This can be a contract deployment, a function call, or a direct
    transfer of tokens to a contract.
    """
    transaction_id: Optional[str] = Field(None, description="Unique identifier for the transaction")
    sender: str = Field(..., description="Address of the transaction sender")
    contract_id: Optional[str] = Field(None, description="ID of the target contract (None for deployment)")
    function: Optional[str] = Field(None, description="Name of the function to call (None for deployment or transfer)")
    arguments: List[Any] = Field(default_factory=list, description="Arguments to pass to the function")
    value: float = Field(0.0, ge=0, description="Amount of PORW tokens to transfer to the contract")
    gas_limit: int = Field(..., gt=0, description="Maximum amount of gas that can be used")
    gas_price: float = Field(..., gt=0, description="Price per unit of gas in PORW tokens")
    timestamp: float = Field(default_factory=time.time, description="Timestamp when the transaction was created")
    signature: Optional[str] = Field(None, description="Digital signature of the transaction data")
    
    # Automatically generate transaction_id if not provided
    @validator('transaction_id', pre=True, always=True)
    def set_transaction_id(cls, v, values):
        if v is None:
            # Create a stable representation for hashing
            tx_data = {
                "sender": values.get('sender'),
                "contract_id": values.get('contract_id'),
                "function": values.get('function'),
                "arguments": values.get('arguments'),
                "value": values.get('value'),
                "gas_limit": values.get('gas_limit'),
                "gas_price": values.get('gas_price'),
                "timestamp": values.get('timestamp', time.time())
            }
            tx_string = json.dumps(tx_data, sort_keys=True)
            return hashlib.sha256(tx_string.encode()).hexdigest()
        return v
    
    def get_signing_data(self) -> bytes:
        """
        Returns the transaction data in a consistent format for signing/verification.
        Excludes the signature itself and the transaction_id (which depends on other fields).
        """
        signing_data = {
            "sender": self.sender,
            "contract_id": self.contract_id,
            "function": self.function,
            "arguments": self.arguments,
            "value": self.value,
            "gas_limit": self.gas_limit,
            "gas_price": self.gas_price,
            "timestamp": self.timestamp
        }
        # Use separators=(',', ':') for compact, deterministic JSON
        return json.dumps(signing_data, sort_keys=True, separators=(',', ':')).encode('utf-8')
    
    def calculate_max_fee(self) -> float:
        """
        Calculate the maximum fee that could be charged for this transaction.
        
        Returns:
            The maximum fee in PORW tokens.
        """
        return self.gas_limit * self.gas_price


class ContractExecutionResult(BaseModel):
    """
    Represents the result of executing a smart contract function.
    """
    success: bool = Field(..., description="Whether the execution was successful")
    return_value: Any = Field(None, description="Return value of the function call")
    gas_used: int = Field(..., ge=0, description="Amount of gas used during execution")
    logs: List[str] = Field(default_factory=list, description="Logs generated during execution")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    state_changes: Dict[str, Any] = Field(default_factory=dict, description="Changes to the contract's state")
    events: List[Dict[str, Any]] = Field(default_factory=list, description="Events emitted during execution")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContractExecutionResult':
        """Create a result from a dictionary."""
        return cls(**data)


class ContractEvent(BaseModel):
    """
    Represents an event emitted by a smart contract.
    """
    contract_id: str = Field(..., description="ID of the contract that emitted the event")
    name: str = Field(..., description="Name of the event")
    data: Dict[str, Any] = Field(..., description="Event data")
    block_index: Optional[int] = Field(None, description="Index of the block containing the event")
    transaction_id: str = Field(..., description="ID of the transaction that triggered the event")
    timestamp: float = Field(default_factory=time.time, description="Timestamp when the event was emitted")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContractEvent':
        """Create an event from a dictionary."""
        return cls(**data)
