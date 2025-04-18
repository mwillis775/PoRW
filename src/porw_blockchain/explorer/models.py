# src/porw_blockchain/explorer/models.py
"""
Data models for the blockchain explorer API.

This module defines the data models used by the blockchain explorer API,
including blocks, transactions, addresses, and network statistics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union


@dataclass
class BlockSummary:
    """Summary information about a block."""
    height: int
    hash: str
    timestamp: int
    transaction_count: int
    size: int
    block_type: str  # 'PoRW' or 'PoRS'
    creator: str
    
    @property
    def datetime(self) -> datetime:
        """Get the block timestamp as a datetime object."""
        return datetime.fromtimestamp(self.timestamp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'height': self.height,
            'hash': self.hash,
            'timestamp': self.timestamp,
            'datetime': self.datetime.isoformat(),
            'transaction_count': self.transaction_count,
            'size': self.size,
            'block_type': self.block_type,
            'creator': self.creator
        }


@dataclass
class TransactionSummary:
    """Summary information about a transaction."""
    id: str
    block_height: Optional[int]
    block_hash: Optional[str]
    timestamp: int
    sender: str
    recipient: str
    amount: float
    fee: float
    status: str  # 'pending', 'confirmed', 'failed'
    
    @property
    def datetime(self) -> datetime:
        """Get the transaction timestamp as a datetime object."""
        return datetime.fromtimestamp(self.timestamp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'block_height': self.block_height,
            'block_hash': self.block_hash,
            'timestamp': self.timestamp,
            'datetime': self.datetime.isoformat(),
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'fee': self.fee,
            'status': self.status
        }


@dataclass
class AddressSummary:
    """Summary information about an address."""
    address: str
    balance: float
    transaction_count: int
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None
    
    @property
    def first_seen_datetime(self) -> Optional[datetime]:
        """Get the first seen timestamp as a datetime object."""
        return datetime.fromtimestamp(self.first_seen) if self.first_seen else None
    
    @property
    def last_seen_datetime(self) -> Optional[datetime]:
        """Get the last seen timestamp as a datetime object."""
        return datetime.fromtimestamp(self.last_seen) if self.last_seen else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            'address': self.address,
            'balance': self.balance,
            'transaction_count': self.transaction_count
        }
        
        if self.first_seen:
            result['first_seen'] = self.first_seen
            result['first_seen_datetime'] = self.first_seen_datetime.isoformat()
            
        if self.last_seen:
            result['last_seen'] = self.last_seen
            result['last_seen_datetime'] = self.last_seen_datetime.isoformat()
            
        return result


@dataclass
class NetworkStats:
    """Network statistics."""
    height: int
    total_transactions: int
    total_addresses: int
    average_block_time: float  # in seconds
    difficulty: float
    hash_rate: float
    total_supply: float
    circulating_supply: float
    transaction_count_24h: int
    average_transaction_fee_24h: float
    active_nodes: int
    mining_nodes: int
    storage_nodes: int
    protein_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'height': self.height,
            'total_transactions': self.total_transactions,
            'total_addresses': self.total_addresses,
            'average_block_time': self.average_block_time,
            'difficulty': self.difficulty,
            'hash_rate': self.hash_rate,
            'total_supply': self.total_supply,
            'circulating_supply': self.circulating_supply,
            'transaction_count_24h': self.transaction_count_24h,
            'average_transaction_fee_24h': self.average_transaction_fee_24h,
            'active_nodes': self.active_nodes,
            'mining_nodes': self.mining_nodes,
            'storage_nodes': self.storage_nodes,
            'protein_count': self.protein_count
        }


@dataclass
class ProteinSummary:
    """Summary information about a protein."""
    id: str
    name: str
    energy_score: float
    folding_timestamp: int
    scientific_value: float
    
    @property
    def folding_datetime(self) -> datetime:
        """Get the folding timestamp as a datetime object."""
        return datetime.fromtimestamp(self.folding_timestamp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'energy_score': self.energy_score,
            'folding_timestamp': self.folding_timestamp,
            'folding_datetime': self.folding_datetime.isoformat(),
            'scientific_value': self.scientific_value
        }


@dataclass
class StorageNodeSummary:
    """Summary information about a storage node."""
    id: str
    address: str
    status: str  # 'online', 'offline', 'syncing'
    capacity: int  # in bytes
    used: int  # in bytes
    reliability: float  # 0-100
    last_seen: int
    
    @property
    def last_seen_datetime(self) -> datetime:
        """Get the last seen timestamp as a datetime object."""
        return datetime.fromtimestamp(self.last_seen)
    
    @property
    def usage_percentage(self) -> float:
        """Get the usage percentage."""
        return (self.used / self.capacity) * 100 if self.capacity > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'address': self.address,
            'status': self.status,
            'capacity': self.capacity,
            'used': self.used,
            'usage_percentage': self.usage_percentage,
            'reliability': self.reliability,
            'last_seen': self.last_seen,
            'last_seen_datetime': self.last_seen_datetime.isoformat()
        }


@dataclass
class BlockDetail(BlockSummary):
    """Detailed information about a block."""
    previous_hash: str
    merkle_root: str
    nonce: int
    difficulty: float
    version: int
    transactions: List[TransactionSummary] = field(default_factory=list)
    porw_data: Optional[Dict[str, Any]] = None
    pors_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result.update({
            'previous_hash': self.previous_hash,
            'merkle_root': self.merkle_root,
            'nonce': self.nonce,
            'difficulty': self.difficulty,
            'version': self.version,
            'transactions': [tx.to_dict() for tx in self.transactions]
        })
        
        if self.porw_data:
            result['porw_data'] = self.porw_data
            
        if self.pors_data:
            result['pors_data'] = self.pors_data
            
        return result


@dataclass
class TransactionDetail(TransactionSummary):
    """Detailed information about a transaction."""
    nonce: int
    memo: Optional[str] = None
    is_memo_encrypted: bool = False
    confirmations: int = 0
    type: str = 'regular'  # 'regular', 'contract', 'confidential'
    contract_data: Optional[Dict[str, Any]] = None
    confidential_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result.update({
            'nonce': self.nonce,
            'confirmations': self.confirmations,
            'type': self.type
        })
        
        if self.memo:
            result['memo'] = self.memo
            result['is_memo_encrypted'] = self.is_memo_encrypted
            
        if self.contract_data:
            result['contract_data'] = self.contract_data
            
        if self.confidential_data:
            result['confidential_data'] = self.confidential_data
            
        return result


@dataclass
class AddressDetail(AddressSummary):
    """Detailed information about an address."""
    sent_amount: float = 0.0
    received_amount: float = 0.0
    transactions: List[TransactionSummary] = field(default_factory=list)
    is_contract: bool = False
    contract_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result.update({
            'sent_amount': self.sent_amount,
            'received_amount': self.received_amount,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'is_contract': self.is_contract
        })
        
        if self.contract_data:
            result['contract_data'] = self.contract_data
            
        return result


@dataclass
class ProteinDetail(ProteinSummary):
    """Detailed information about a protein."""
    sequence: str
    structure: Optional[Dict[str, Any]] = None
    folding_method: Optional[str] = None
    scientific_value_details: Optional[Dict[str, float]] = None
    references: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result.update({
            'sequence': self.sequence
        })
        
        if self.structure:
            result['structure'] = self.structure
            
        if self.folding_method:
            result['folding_method'] = self.folding_method
            
        if self.scientific_value_details:
            result['scientific_value_details'] = self.scientific_value_details
            
        if self.references:
            result['references'] = self.references
            
        if self.metadata:
            result['metadata'] = self.metadata
            
        return result


@dataclass
class StorageNodeDetail(StorageNodeSummary):
    """Detailed information about a storage node."""
    version: str
    uptime: int  # in seconds
    location: Optional[Dict[str, Any]] = None
    stored_data: List[Dict[str, Any]] = field(default_factory=list)
    rewards: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result.update({
            'version': self.version,
            'uptime': self.uptime,
            'stored_data': self.stored_data
        })
        
        if self.location:
            result['location'] = self.location
            
        if self.rewards:
            result['rewards'] = self.rewards
            
        return result
