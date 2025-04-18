# src/porw_blockchain/explorer/__init__.py
"""
Blockchain explorer package for the PoRW blockchain.

This package provides functionality for exploring and querying the blockchain,
including blocks, transactions, addresses, and network statistics.
"""

from .api import ExplorerAPI, create_explorer_api
from .models import (
    BlockSummary,
    BlockDetail,
    TransactionSummary,
    TransactionDetail,
    AddressSummary,
    AddressDetail,
    NetworkStats,
    ProteinSummary,
    ProteinDetail,
    StorageNodeSummary,
    StorageNodeDetail
)

__all__ = [
    'ExplorerAPI',
    'create_explorer_api',
    'BlockSummary',
    'BlockDetail',
    'TransactionSummary',
    'TransactionDetail',
    'AddressSummary',
    'AddressDetail',
    'NetworkStats',
    'ProteinSummary',
    'ProteinDetail',
    'StorageNodeSummary',
    'StorageNodeDetail'
]
