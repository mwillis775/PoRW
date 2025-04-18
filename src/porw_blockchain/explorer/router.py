# src/porw_blockchain/explorer/router.py
"""
FastAPI router for the blockchain explorer API.

This module provides a FastAPI router for the blockchain explorer API,
exposing endpoints for exploring and querying the blockchain.
"""

import logging
from typing import Dict, List, Optional, Any, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field

from ..core.blockchain import Blockchain
from ..storage.database import Database
from .api import ExplorerAPI, create_explorer_api

# Configure logger
logger = logging.getLogger(__name__)


# Pydantic models for API responses
class BlockSummaryResponse(BaseModel):
    """Block summary response model."""
    height: int = Field(..., description="Block height")
    hash: str = Field(..., description="Block hash")
    timestamp: int = Field(..., description="Block timestamp (Unix time)")
    datetime: str = Field(..., description="Block timestamp (ISO format)")
    transaction_count: int = Field(..., description="Number of transactions in the block")
    size: int = Field(..., description="Block size in bytes")
    block_type: str = Field(..., description="Block type (PoRW or PoRS)")
    creator: str = Field(..., description="Block creator address")


class TransactionSummaryResponse(BaseModel):
    """Transaction summary response model."""
    id: str = Field(..., description="Transaction ID")
    block_height: Optional[int] = Field(None, description="Block height")
    block_hash: Optional[str] = Field(None, description="Block hash")
    timestamp: int = Field(..., description="Transaction timestamp (Unix time)")
    datetime: str = Field(..., description="Transaction timestamp (ISO format)")
    sender: str = Field(..., description="Sender address")
    recipient: str = Field(..., description="Recipient address")
    amount: float = Field(..., description="Transaction amount")
    fee: float = Field(..., description="Transaction fee")
    status: str = Field(..., description="Transaction status (pending, confirmed, failed)")


class AddressSummaryResponse(BaseModel):
    """Address summary response model."""
    address: str = Field(..., description="Wallet address")
    balance: float = Field(..., description="Address balance")
    transaction_count: int = Field(..., description="Number of transactions")
    first_seen: Optional[int] = Field(None, description="First seen timestamp (Unix time)")
    first_seen_datetime: Optional[str] = Field(None, description="First seen timestamp (ISO format)")
    last_seen: Optional[int] = Field(None, description="Last seen timestamp (Unix time)")
    last_seen_datetime: Optional[str] = Field(None, description="Last seen timestamp (ISO format)")


class NetworkStatsResponse(BaseModel):
    """Network statistics response model."""
    height: int = Field(..., description="Current blockchain height")
    total_transactions: int = Field(..., description="Total number of transactions")
    total_addresses: int = Field(..., description="Total number of addresses")
    average_block_time: float = Field(..., description="Average block time in seconds")
    difficulty: float = Field(..., description="Current mining difficulty")
    hash_rate: float = Field(..., description="Current hash rate")
    total_supply: float = Field(..., description="Total supply of tokens")
    circulating_supply: float = Field(..., description="Circulating supply of tokens")
    transaction_count_24h: int = Field(..., description="Number of transactions in the last 24 hours")
    average_transaction_fee_24h: float = Field(..., description="Average transaction fee in the last 24 hours")
    active_nodes: int = Field(..., description="Number of active nodes")
    mining_nodes: int = Field(..., description="Number of mining nodes")
    storage_nodes: int = Field(..., description="Number of storage nodes")
    protein_count: int = Field(..., description="Number of proteins")


class ProteinSummaryResponse(BaseModel):
    """Protein summary response model."""
    id: str = Field(..., description="Protein ID")
    name: str = Field(..., description="Protein name")
    energy_score: float = Field(..., description="Energy score")
    folding_timestamp: int = Field(..., description="Folding timestamp (Unix time)")
    folding_datetime: str = Field(..., description="Folding timestamp (ISO format)")
    scientific_value: float = Field(..., description="Scientific value")


class StorageNodeSummaryResponse(BaseModel):
    """Storage node summary response model."""
    id: str = Field(..., description="Storage node ID")
    address: str = Field(..., description="Storage node address")
    status: str = Field(..., description="Storage node status (online, offline, syncing)")
    capacity: int = Field(..., description="Storage capacity in bytes")
    used: int = Field(..., description="Used storage in bytes")
    usage_percentage: float = Field(..., description="Usage percentage")
    reliability: float = Field(..., description="Reliability score (0-100)")
    last_seen: int = Field(..., description="Last seen timestamp (Unix time)")
    last_seen_datetime: str = Field(..., description="Last seen timestamp (ISO format)")


class BlockDetailResponse(BlockSummaryResponse):
    """Block detail response model."""
    previous_hash: str = Field(..., description="Previous block hash")
    merkle_root: str = Field(..., description="Merkle root of transactions")
    nonce: int = Field(..., description="Block nonce")
    difficulty: float = Field(..., description="Block difficulty")
    version: int = Field(..., description="Block version")
    transactions: List[TransactionSummaryResponse] = Field([], description="Transactions in the block")
    porw_data: Optional[Dict[str, Any]] = Field(None, description="PoRW-specific data")
    pors_data: Optional[Dict[str, Any]] = Field(None, description="PoRS-specific data")


class TransactionDetailResponse(TransactionSummaryResponse):
    """Transaction detail response model."""
    nonce: int = Field(..., description="Transaction nonce")
    memo: Optional[str] = Field(None, description="Transaction memo")
    is_memo_encrypted: Optional[bool] = Field(None, description="Whether the memo is encrypted")
    confirmations: int = Field(..., description="Number of confirmations")
    type: str = Field(..., description="Transaction type (regular, contract, confidential)")
    contract_data: Optional[Dict[str, Any]] = Field(None, description="Contract-specific data")
    confidential_data: Optional[Dict[str, Any]] = Field(None, description="Confidential transaction data")


class AddressDetailResponse(AddressSummaryResponse):
    """Address detail response model."""
    sent_amount: float = Field(..., description="Total amount sent")
    received_amount: float = Field(..., description="Total amount received")
    transactions: List[TransactionSummaryResponse] = Field([], description="Recent transactions")
    is_contract: bool = Field(..., description="Whether the address is a contract")
    contract_data: Optional[Dict[str, Any]] = Field(None, description="Contract-specific data")


class ProteinDetailResponse(ProteinSummaryResponse):
    """Protein detail response model."""
    sequence: str = Field(..., description="Amino acid sequence")
    structure: Optional[Dict[str, Any]] = Field(None, description="Protein structure data")
    folding_method: Optional[str] = Field(None, description="Folding method")
    scientific_value_details: Optional[Dict[str, float]] = Field(None, description="Scientific value details")
    references: List[Dict[str, Any]] = Field([], description="References to scientific literature")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata")


class StorageNodeDetailResponse(StorageNodeSummaryResponse):
    """Storage node detail response model."""
    version: str = Field(..., description="Node version")
    uptime: int = Field(..., description="Uptime in seconds")
    location: Optional[Dict[str, Any]] = Field(None, description="Node location")
    stored_data: List[Dict[str, Any]] = Field([], description="Stored data")
    rewards: Optional[Dict[str, Any]] = Field(None, description="Node rewards")


class SearchResponse(BaseModel):
    """Search response model."""
    blocks: List[Dict[str, Any]] = Field([], description="Block results")
    transactions: List[Dict[str, Any]] = Field([], description="Transaction results")
    addresses: List[Dict[str, Any]] = Field([], description="Address results")
    proteins: List[Dict[str, Any]] = Field([], description="Protein results")
    storage_nodes: List[Dict[str, Any]] = Field([], description="Storage node results")


class APIResponse(BaseModel):
    """API response model."""
    success: bool = Field(..., description="Success status")
    data: Any = Field(..., description="Response data")
    error: Optional[str] = Field(None, description="Error message")


# Create router
router = APIRouter(
    prefix="/explorer",
    tags=["explorer"],
    responses={404: {"description": "Not found"}},
)


# Dependency to get the explorer API
def get_explorer_api(
    blockchain: Blockchain = Depends(lambda: Blockchain()),
    database: Database = Depends(lambda: Database())
) -> ExplorerAPI:
    """
    Get the explorer API.

    Args:
        blockchain: Blockchain instance
        database: Database instance

    Returns:
        ExplorerAPI instance
    """
    return create_explorer_api(blockchain, database)


@router.get(
    "/blocks/height/{height}",
    response_model=APIResponse,
    summary="Get block by height",
    description="Get detailed information about a block by its height."
)
async def get_block_by_height(
    height: int = Path(..., description="Block height"),
    explorer_api: ExplorerAPI = Depends(get_explorer_api)
):
    """
    Get a block by its height.

    Args:
        height: Block height
        explorer_api: Explorer API instance

    Returns:
        Block details
    """
    try:
        block = explorer_api.get_block_by_height(height)
        if not block:
            return {
                "success": False,
                "data": None,
                "error": f"Block with height {height} not found"
            }
        
        return {
            "success": True,
            "data": block.to_dict(),
            "error": None
        }
    except Exception as e:
        logger.error(f"Error getting block by height {height}: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.get(
    "/blocks/hash/{hash}",
    response_model=APIResponse,
    summary="Get block by hash",
    description="Get detailed information about a block by its hash."
)
async def get_block_by_hash(
    hash: str = Path(..., description="Block hash"),
    explorer_api: ExplorerAPI = Depends(get_explorer_api)
):
    """
    Get a block by its hash.

    Args:
        hash: Block hash
        explorer_api: Explorer API instance

    Returns:
        Block details
    """
    try:
        block = explorer_api.get_block_by_hash(hash)
        if not block:
            return {
                "success": False,
                "data": None,
                "error": f"Block with hash {hash} not found"
            }
        
        return {
            "success": True,
            "data": block.to_dict(),
            "error": None
        }
    except Exception as e:
        logger.error(f"Error getting block by hash {hash}: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.get(
    "/blocks/latest",
    response_model=APIResponse,
    summary="Get latest blocks",
    description="Get a list of the latest blocks."
)
async def get_latest_blocks(
    limit: int = Query(10, description="Maximum number of blocks to return"),
    offset: int = Query(0, description="Offset for pagination"),
    explorer_api: ExplorerAPI = Depends(get_explorer_api)
):
    """
    Get the latest blocks.

    Args:
        limit: Maximum number of blocks to return
        offset: Offset for pagination
        explorer_api: Explorer API instance

    Returns:
        List of block summaries
    """
    try:
        blocks = explorer_api.get_latest_blocks(limit, offset)
        return {
            "success": True,
            "data": [block.to_dict() for block in blocks],
            "error": None
        }
    except Exception as e:
        logger.error(f"Error getting latest blocks: {e}")
        return {
            "success": False,
            "data": [],
            "error": str(e)
        }


@router.get(
    "/transactions/{tx_id}",
    response_model=APIResponse,
    summary="Get transaction",
    description="Get detailed information about a transaction by its ID."
)
async def get_transaction(
    tx_id: str = Path(..., description="Transaction ID"),
    explorer_api: ExplorerAPI = Depends(get_explorer_api)
):
    """
    Get a transaction by its ID.

    Args:
        tx_id: Transaction ID
        explorer_api: Explorer API instance

    Returns:
        Transaction details
    """
    try:
        transaction = explorer_api.get_transaction(tx_id)
        if not transaction:
            return {
                "success": False,
                "data": None,
                "error": f"Transaction with ID {tx_id} not found"
            }
        
        return {
            "success": True,
            "data": transaction.to_dict(),
            "error": None
        }
    except Exception as e:
        logger.error(f"Error getting transaction {tx_id}: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.get(
    "/blocks/{block_hash}/transactions",
    response_model=APIResponse,
    summary="Get transactions by block",
    description="Get a list of transactions in a block."
)
async def get_transactions_by_block(
    block_hash: str = Path(..., description="Block hash"),
    limit: int = Query(50, description="Maximum number of transactions to return"),
    offset: int = Query(0, description="Offset for pagination"),
    explorer_api: ExplorerAPI = Depends(get_explorer_api)
):
    """
    Get transactions in a block.

    Args:
        block_hash: Block hash
        limit: Maximum number of transactions to return
        offset: Offset for pagination
        explorer_api: Explorer API instance

    Returns:
        List of transaction summaries
    """
    try:
        transactions = explorer_api.get_transactions_by_block(block_hash, limit, offset)
        return {
            "success": True,
            "data": [tx.to_dict() for tx in transactions],
            "error": None
        }
    except Exception as e:
        logger.error(f"Error getting transactions for block {block_hash}: {e}")
        return {
            "success": False,
            "data": [],
            "error": str(e)
        }


@router.get(
    "/addresses/{address}/transactions",
    response_model=APIResponse,
    summary="Get transactions by address",
    description="Get a list of transactions for an address."
)
async def get_transactions_by_address(
    address: str = Path(..., description="Wallet address"),
    limit: int = Query(50, description="Maximum number of transactions to return"),
    offset: int = Query(0, description="Offset for pagination"),
    explorer_api: ExplorerAPI = Depends(get_explorer_api)
):
    """
    Get transactions for an address.

    Args:
        address: Wallet address
        limit: Maximum number of transactions to return
        offset: Offset for pagination
        explorer_api: Explorer API instance

    Returns:
        List of transaction summaries
    """
    try:
        transactions = explorer_api.get_transactions_by_address(address, limit, offset)
        return {
            "success": True,
            "data": [tx.to_dict() for tx in transactions],
            "error": None
        }
    except Exception as e:
        logger.error(f"Error getting transactions for address {address}: {e}")
        return {
            "success": False,
            "data": [],
            "error": str(e)
        }


@router.get(
    "/addresses/{address}",
    response_model=APIResponse,
    summary="Get address",
    description="Get detailed information about an address."
)
async def get_address(
    address: str = Path(..., description="Wallet address"),
    explorer_api: ExplorerAPI = Depends(get_explorer_api)
):
    """
    Get address details.

    Args:
        address: Wallet address
        explorer_api: Explorer API instance

    Returns:
        Address details
    """
    try:
        address_detail = explorer_api.get_address(address)
        if not address_detail:
            return {
                "success": False,
                "data": None,
                "error": f"Address {address} not found"
            }
        
        return {
            "success": True,
            "data": address_detail.to_dict(),
            "error": None
        }
    except Exception as e:
        logger.error(f"Error getting address {address}: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.get(
    "/stats",
    response_model=APIResponse,
    summary="Get network statistics",
    description="Get statistics about the network."
)
async def get_network_stats(
    explorer_api: ExplorerAPI = Depends(get_explorer_api)
):
    """
    Get network statistics.

    Args:
        explorer_api: Explorer API instance

    Returns:
        Network statistics
    """
    try:
        stats = explorer_api.get_network_stats()
        return {
            "success": True,
            "data": stats.to_dict(),
            "error": None
        }
    except Exception as e:
        logger.error(f"Error getting network stats: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.get(
    "/proteins/{protein_id}",
    response_model=APIResponse,
    summary="Get protein",
    description="Get detailed information about a protein."
)
async def get_protein(
    protein_id: str = Path(..., description="Protein ID"),
    explorer_api: ExplorerAPI = Depends(get_explorer_api)
):
    """
    Get protein details.

    Args:
        protein_id: Protein ID
        explorer_api: Explorer API instance

    Returns:
        Protein details
    """
    try:
        protein = explorer_api.get_protein(protein_id)
        if not protein:
            return {
                "success": False,
                "data": None,
                "error": f"Protein with ID {protein_id} not found"
            }
        
        return {
            "success": True,
            "data": protein.to_dict(),
            "error": None
        }
    except Exception as e:
        logger.error(f"Error getting protein {protein_id}: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.get(
    "/proteins",
    response_model=APIResponse,
    summary="Get proteins",
    description="Get a list of proteins."
)
async def get_proteins(
    limit: int = Query(50, description="Maximum number of proteins to return"),
    offset: int = Query(0, description="Offset for pagination"),
    explorer_api: ExplorerAPI = Depends(get_explorer_api)
):
    """
    Get proteins.

    Args:
        limit: Maximum number of proteins to return
        offset: Offset for pagination
        explorer_api: Explorer API instance

    Returns:
        List of protein summaries
    """
    try:
        proteins = explorer_api.get_proteins(limit, offset)
        return {
            "success": True,
            "data": [protein.to_dict() for protein in proteins],
            "error": None
        }
    except Exception as e:
        logger.error(f"Error getting proteins: {e}")
        return {
            "success": False,
            "data": [],
            "error": str(e)
        }


@router.get(
    "/storage-nodes/{node_id}",
    response_model=APIResponse,
    summary="Get storage node",
    description="Get detailed information about a storage node."
)
async def get_storage_node(
    node_id: str = Path(..., description="Storage node ID"),
    explorer_api: ExplorerAPI = Depends(get_explorer_api)
):
    """
    Get storage node details.

    Args:
        node_id: Storage node ID
        explorer_api: Explorer API instance

    Returns:
        Storage node details
    """
    try:
        node = explorer_api.get_storage_node(node_id)
        if not node:
            return {
                "success": False,
                "data": None,
                "error": f"Storage node with ID {node_id} not found"
            }
        
        return {
            "success": True,
            "data": node.to_dict(),
            "error": None
        }
    except Exception as e:
        logger.error(f"Error getting storage node {node_id}: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.get(
    "/storage-nodes",
    response_model=APIResponse,
    summary="Get storage nodes",
    description="Get a list of storage nodes."
)
async def get_storage_nodes(
    limit: int = Query(50, description="Maximum number of storage nodes to return"),
    offset: int = Query(0, description="Offset for pagination"),
    explorer_api: ExplorerAPI = Depends(get_explorer_api)
):
    """
    Get storage nodes.

    Args:
        limit: Maximum number of storage nodes to return
        offset: Offset for pagination
        explorer_api: Explorer API instance

    Returns:
        List of storage node summaries
    """
    try:
        nodes = explorer_api.get_storage_nodes(limit, offset)
        return {
            "success": True,
            "data": [node.to_dict() for node in nodes],
            "error": None
        }
    except Exception as e:
        logger.error(f"Error getting storage nodes: {e}")
        return {
            "success": False,
            "data": [],
            "error": str(e)
        }


@router.get(
    "/search",
    response_model=APIResponse,
    summary="Search",
    description="Search for blocks, transactions, addresses, proteins, or storage nodes."
)
async def search(
    query: str = Query(..., description="Search query"),
    explorer_api: ExplorerAPI = Depends(get_explorer_api)
):
    """
    Search for blocks, transactions, addresses, proteins, or storage nodes.

    Args:
        query: Search query
        explorer_api: Explorer API instance

    Returns:
        Search results
    """
    try:
        results = explorer_api.search(query)
        return {
            "success": True,
            "data": results,
            "error": None
        }
    except Exception as e:
        logger.error(f"Error searching for {query}: {e}")
        return {
            "success": False,
            "data": {
                "blocks": [],
                "transactions": [],
                "addresses": [],
                "proteins": [],
                "storage_nodes": []
            },
            "error": str(e)
        }
