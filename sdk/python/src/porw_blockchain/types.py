"""
Type definitions for the PoRW Blockchain SDK.
"""

from typing import Dict, List, Optional, Any, Union, TypedDict


class BlockchainInfo(TypedDict, total=False):
    """Blockchain information."""

    height: int
    latest_block_hash: str
    latest_block_timestamp: int
    total_transactions: int
    difficulty: float
    network: str
    protocol_version: str
    connected_peers: int
    sync_status: str
    sync_progress: Optional[float]


class PoRWData(TypedDict, total=False):
    """PoRW-specific block data."""

    protein_id: str
    folding_result_hash: str
    energy_score: float
    minted_amount: float


class PoRSData(TypedDict, total=False):
    """PoRS-specific block data."""

    storage_proof_hash: str
    quorum_signatures: List[str]
    storage_rewards: List[Dict[str, Union[str, float]]]


class Block(TypedDict, total=False):
    """Block data."""

    hash: str
    height: int
    previous_hash: str
    timestamp: int
    block_type: str
    creator: str
    transactions: List["Transaction"]
    size: int
    difficulty: float
    nonce: int
    version: int
    merkle_root: str
    porw_data: Optional[PoRWData]
    pors_data: Optional[PoRSData]


class ContractData(TypedDict, total=False):
    """Contract-specific transaction data."""

    contract_address: str
    function: str
    arguments: List[Any]


class ConfidentialData(TypedDict, total=False):
    """Confidential transaction data."""

    commitment: str
    range_proof: str


class Transaction(TypedDict, total=False):
    """Transaction data."""

    id: str
    sender: str
    recipient: str
    amount: float
    fee: float
    timestamp: int
    nonce: int
    memo: Optional[str]
    is_memo_encrypted: Optional[bool]
    signature: str
    block_hash: Optional[str]
    block_height: Optional[int]
    status: str
    confirmations: Optional[int]
    type: Optional[str]
    contract_data: Optional[ContractData]
    confidential_data: Optional[ConfidentialData]


class TransactionReceipt(TypedDict, total=False):
    """Transaction receipt."""

    transaction_id: str
    block_hash: str
    block_height: int
    transaction_index: int
    gas_used: Optional[int]
    status: str
    error: Optional[str]
    events: Optional[List[Any]]


class NetworkStats(TypedDict, total=False):
    """Network statistics."""

    total_nodes: int
    mining_nodes: int
    storage_nodes: int
    average_block_time: float
    hash_rate: float
    total_supply: float
    circulating_supply: float
    transaction_count_24h: int
    average_transaction_fee_24h: float
    uptime: int
    protocol_version: str


class ProteinStructure(TypedDict, total=False):
    """Protein structure data."""

    format: str
    data: str
    visualization_url: Optional[str]


class ScientificValue(TypedDict, total=False):
    """Scientific value assessment."""

    novelty: float
    quality: float
    relevance: float
    overall: float


class Reference(TypedDict, total=False):
    """Scientific literature reference."""

    title: str
    url: str
    authors: List[str]
    date: str


class ProteinData(TypedDict, total=False):
    """Protein data."""

    id: str
    name: str
    sequence: str
    structure: Optional[ProteinStructure]
    energy_score: Optional[float]
    folding_timestamp: Optional[int]
    folding_method: Optional[str]
    scientific_value: Optional[ScientificValue]
    references: Optional[List[Reference]]
    metadata: Optional[Dict[str, Any]]


class Location(TypedDict, total=False):
    """Geographic location."""

    country: str
    region: Optional[str]
    city: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]


class StorageNodeInfo(TypedDict, total=False):
    """Storage node information."""

    id: str
    address: str
    url: str
    status: str
    capacity: int
    used: int
    uptime: int
    reliability: float
    last_seen: int
    version: str
    location: Optional[Location]


class WalletOptions(TypedDict, total=False):
    """Wallet options."""

    network: Optional[str]
    client: Optional[Any]
    auto_save: Optional[bool]


class TransactionOptions(TypedDict, total=False):
    """Transaction options."""

    fee: Optional[float]
    memo: Optional[str]
    encrypt_memo: Optional[bool]
    recipient_public_key: Optional[str]
    confidential: Optional[bool]
    nonce: Optional[int]


class ContractOptions(TypedDict, total=False):
    """Contract options."""

    address: str
    abi: List[Any]
    wallet: Optional[Any]
    client: Optional[Any]


class HardwareWalletOptions(TypedDict, total=False):
    """Hardware wallet options."""

    type: Optional[str]
    derivation_path: Optional[str]
