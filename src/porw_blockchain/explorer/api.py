# src/porw_blockchain/explorer/api.py
"""
Blockchain explorer API for the PoRW blockchain.

This module provides an API for exploring and querying the blockchain,
including blocks, transactions, addresses, and network statistics.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple, Callable

from ..core.blockchain import Blockchain
from ..core.structures import Block, Transaction
from ..storage.database import Database
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

# Configure logger
logger = logging.getLogger(__name__)


class ExplorerAPI:
    """API for exploring and querying the blockchain."""

    def __init__(self, blockchain: Blockchain, database: Database):
        """
        Initialize the explorer API.

        Args:
            blockchain: Blockchain instance
            database: Database instance
        """
        self.blockchain = blockchain
        self.database = database
        self.cache = {}
        self.cache_expiry = {}
        self.cache_duration = 60  # Cache duration in seconds

    def _get_cached(self, key: str) -> Optional[Any]:
        """
        Get a cached value.

        Args:
            key: Cache key

        Returns:
            Cached value, or None if not found or expired
        """
        if key in self.cache and key in self.cache_expiry:
            if time.time() < self.cache_expiry[key]:
                return self.cache[key]
            else:
                # Remove expired cache entry
                del self.cache[key]
                del self.cache_expiry[key]
        return None

    def _set_cache(self, key: str, value: Any, duration: Optional[int] = None) -> None:
        """
        Set a cached value.

        Args:
            key: Cache key
            value: Value to cache
            duration: Cache duration in seconds (default: self.cache_duration)
        """
        if duration is None:
            duration = self.cache_duration
        self.cache[key] = value
        self.cache_expiry[key] = time.time() + duration

    def _clear_cache(self) -> None:
        """Clear the cache."""
        self.cache.clear()
        self.cache_expiry.clear()

    def get_block_by_height(self, height: int) -> Optional[BlockDetail]:
        """
        Get a block by its height.

        Args:
            height: Block height

        Returns:
            Block details, or None if not found
        """
        cache_key = f"block_height_{height}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # Get block from database
            block_data = self.database.get_block_by_height(height)
            if not block_data:
                return None

            # Convert to BlockDetail
            block = self._convert_to_block_detail(block_data)
            
            # Cache result
            self._set_cache(cache_key, block)
            
            return block
        except Exception as e:
            logger.error(f"Error getting block by height {height}: {e}")
            return None

    def get_block_by_hash(self, hash: str) -> Optional[BlockDetail]:
        """
        Get a block by its hash.

        Args:
            hash: Block hash

        Returns:
            Block details, or None if not found
        """
        cache_key = f"block_hash_{hash}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # Get block from database
            block_data = self.database.get_block_by_hash(hash)
            if not block_data:
                return None

            # Convert to BlockDetail
            block = self._convert_to_block_detail(block_data)
            
            # Cache result
            self._set_cache(cache_key, block)
            
            return block
        except Exception as e:
            logger.error(f"Error getting block by hash {hash}: {e}")
            return None

    def get_latest_blocks(self, limit: int = 10, offset: int = 0) -> List[BlockSummary]:
        """
        Get the latest blocks.

        Args:
            limit: Maximum number of blocks to return (default: 10)
            offset: Offset for pagination (default: 0)

        Returns:
            List of block summaries
        """
        cache_key = f"latest_blocks_{limit}_{offset}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # Get blocks from database
            blocks_data = self.database.get_latest_blocks(limit, offset)
            
            # Convert to BlockSummary
            blocks = [self._convert_to_block_summary(block_data) for block_data in blocks_data]
            
            # Cache result
            self._set_cache(cache_key, blocks)
            
            return blocks
        except Exception as e:
            logger.error(f"Error getting latest blocks: {e}")
            return []

    def get_transaction(self, tx_id: str) -> Optional[TransactionDetail]:
        """
        Get a transaction by its ID.

        Args:
            tx_id: Transaction ID

        Returns:
            Transaction details, or None if not found
        """
        cache_key = f"transaction_{tx_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # Get transaction from database
            tx_data = self.database.get_transaction(tx_id)
            if not tx_data:
                return None

            # Convert to TransactionDetail
            transaction = self._convert_to_transaction_detail(tx_data)
            
            # Cache result
            self._set_cache(cache_key, transaction)
            
            return transaction
        except Exception as e:
            logger.error(f"Error getting transaction {tx_id}: {e}")
            return None

    def get_transactions_by_block(self, block_hash: str, limit: int = 50, offset: int = 0) -> List[TransactionSummary]:
        """
        Get transactions in a block.

        Args:
            block_hash: Block hash
            limit: Maximum number of transactions to return (default: 50)
            offset: Offset for pagination (default: 0)

        Returns:
            List of transaction summaries
        """
        cache_key = f"block_transactions_{block_hash}_{limit}_{offset}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # Get transactions from database
            txs_data = self.database.get_transactions_by_block(block_hash, limit, offset)
            
            # Convert to TransactionSummary
            transactions = [self._convert_to_transaction_summary(tx_data) for tx_data in txs_data]
            
            # Cache result
            self._set_cache(cache_key, transactions)
            
            return transactions
        except Exception as e:
            logger.error(f"Error getting transactions for block {block_hash}: {e}")
            return []

    def get_transactions_by_address(self, address: str, limit: int = 50, offset: int = 0) -> List[TransactionSummary]:
        """
        Get transactions for an address.

        Args:
            address: Wallet address
            limit: Maximum number of transactions to return (default: 50)
            offset: Offset for pagination (default: 0)

        Returns:
            List of transaction summaries
        """
        cache_key = f"address_transactions_{address}_{limit}_{offset}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # Get transactions from database
            txs_data = self.database.get_transactions_by_address(address, limit, offset)
            
            # Convert to TransactionSummary
            transactions = [self._convert_to_transaction_summary(tx_data) for tx_data in txs_data]
            
            # Cache result
            self._set_cache(cache_key, transactions)
            
            return transactions
        except Exception as e:
            logger.error(f"Error getting transactions for address {address}: {e}")
            return []

    def get_address(self, address: str) -> Optional[AddressDetail]:
        """
        Get address details.

        Args:
            address: Wallet address

        Returns:
            Address details, or None if not found
        """
        cache_key = f"address_{address}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # Get address data from database
            address_data = self.database.get_address(address)
            if not address_data:
                return None

            # Get recent transactions
            transactions = self.get_transactions_by_address(address, limit=10)
            
            # Convert to AddressDetail
            address_detail = self._convert_to_address_detail(address_data, transactions)
            
            # Cache result
            self._set_cache(cache_key, address_detail)
            
            return address_detail
        except Exception as e:
            logger.error(f"Error getting address {address}: {e}")
            return None

    def get_network_stats(self) -> NetworkStats:
        """
        Get network statistics.

        Returns:
            Network statistics
        """
        cache_key = "network_stats"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # Get blockchain height
            height = self.blockchain.get_height()
            
            # Get total transactions
            total_transactions = self.database.get_transaction_count()
            
            # Get total addresses
            total_addresses = self.database.get_address_count()
            
            # Get average block time (last 100 blocks)
            blocks = self.database.get_latest_blocks(100)
            if len(blocks) >= 2:
                timestamps = [block['timestamp'] for block in blocks]
                time_diffs = [timestamps[i] - timestamps[i+1] for i in range(len(timestamps)-1)]
                average_block_time = sum(time_diffs) / len(time_diffs)
            else:
                average_block_time = 0
            
            # Get difficulty
            difficulty = self.blockchain.get_difficulty()
            
            # Get hash rate
            hash_rate = difficulty * (2**32) / average_block_time if average_block_time > 0 else 0
            
            # Get total supply
            total_supply = self.database.get_total_supply()
            
            # Get circulating supply
            circulating_supply = self.database.get_circulating_supply()
            
            # Get transaction count in last 24 hours
            timestamp_24h_ago = int(time.time()) - 86400
            transaction_count_24h = self.database.get_transaction_count_since(timestamp_24h_ago)
            
            # Get average transaction fee in last 24 hours
            average_transaction_fee_24h = self.database.get_average_transaction_fee_since(timestamp_24h_ago)
            
            # Get node counts
            active_nodes = self.database.get_active_node_count()
            mining_nodes = self.database.get_mining_node_count()
            storage_nodes = self.database.get_storage_node_count()
            
            # Get protein count
            protein_count = self.database.get_protein_count()
            
            # Create NetworkStats
            stats = NetworkStats(
                height=height,
                total_transactions=total_transactions,
                total_addresses=total_addresses,
                average_block_time=average_block_time,
                difficulty=difficulty,
                hash_rate=hash_rate,
                total_supply=total_supply,
                circulating_supply=circulating_supply,
                transaction_count_24h=transaction_count_24h,
                average_transaction_fee_24h=average_transaction_fee_24h,
                active_nodes=active_nodes,
                mining_nodes=mining_nodes,
                storage_nodes=storage_nodes,
                protein_count=protein_count
            )
            
            # Cache result
            self._set_cache(cache_key, stats, duration=30)  # Shorter cache duration for stats
            
            return stats
        except Exception as e:
            logger.error(f"Error getting network stats: {e}")
            # Return default stats on error
            return NetworkStats(
                height=0,
                total_transactions=0,
                total_addresses=0,
                average_block_time=0,
                difficulty=0,
                hash_rate=0,
                total_supply=0,
                circulating_supply=0,
                transaction_count_24h=0,
                average_transaction_fee_24h=0,
                active_nodes=0,
                mining_nodes=0,
                storage_nodes=0,
                protein_count=0
            )

    def get_protein(self, protein_id: str) -> Optional[ProteinDetail]:
        """
        Get protein details.

        Args:
            protein_id: Protein ID

        Returns:
            Protein details, or None if not found
        """
        cache_key = f"protein_{protein_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # Get protein data from database
            protein_data = self.database.get_protein(protein_id)
            if not protein_data:
                return None

            # Convert to ProteinDetail
            protein = self._convert_to_protein_detail(protein_data)
            
            # Cache result
            self._set_cache(cache_key, protein)
            
            return protein
        except Exception as e:
            logger.error(f"Error getting protein {protein_id}: {e}")
            return None

    def get_proteins(self, limit: int = 50, offset: int = 0) -> List[ProteinSummary]:
        """
        Get proteins.

        Args:
            limit: Maximum number of proteins to return (default: 50)
            offset: Offset for pagination (default: 0)

        Returns:
            List of protein summaries
        """
        cache_key = f"proteins_{limit}_{offset}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # Get proteins from database
            proteins_data = self.database.get_proteins(limit, offset)
            
            # Convert to ProteinSummary
            proteins = [self._convert_to_protein_summary(protein_data) for protein_data in proteins_data]
            
            # Cache result
            self._set_cache(cache_key, proteins)
            
            return proteins
        except Exception as e:
            logger.error(f"Error getting proteins: {e}")
            return []

    def get_storage_node(self, node_id: str) -> Optional[StorageNodeDetail]:
        """
        Get storage node details.

        Args:
            node_id: Storage node ID

        Returns:
            Storage node details, or None if not found
        """
        cache_key = f"storage_node_{node_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # Get storage node data from database
            node_data = self.database.get_storage_node(node_id)
            if not node_data:
                return None

            # Convert to StorageNodeDetail
            node = self._convert_to_storage_node_detail(node_data)
            
            # Cache result
            self._set_cache(cache_key, node)
            
            return node
        except Exception as e:
            logger.error(f"Error getting storage node {node_id}: {e}")
            return None

    def get_storage_nodes(self, limit: int = 50, offset: int = 0) -> List[StorageNodeSummary]:
        """
        Get storage nodes.

        Args:
            limit: Maximum number of storage nodes to return (default: 50)
            offset: Offset for pagination (default: 0)

        Returns:
            List of storage node summaries
        """
        cache_key = f"storage_nodes_{limit}_{offset}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # Get storage nodes from database
            nodes_data = self.database.get_storage_nodes(limit, offset)
            
            # Convert to StorageNodeSummary
            nodes = [self._convert_to_storage_node_summary(node_data) for node_data in nodes_data]
            
            # Cache result
            self._set_cache(cache_key, nodes)
            
            return nodes
        except Exception as e:
            logger.error(f"Error getting storage nodes: {e}")
            return []

    def search(self, query: str) -> Dict[str, Any]:
        """
        Search for blocks, transactions, addresses, proteins, or storage nodes.

        Args:
            query: Search query

        Returns:
            Dictionary containing search results
        """
        try:
            results = {
                'blocks': [],
                'transactions': [],
                'addresses': [],
                'proteins': [],
                'storage_nodes': []
            }
            
            # Check if query is a block height
            try:
                height = int(query)
                block = self.get_block_by_height(height)
                if block:
                    results['blocks'].append(block.to_dict())
            except ValueError:
                pass
            
            # Check if query is a block hash
            if len(query) == 64:  # Assuming SHA-256 hash
                block = self.get_block_by_hash(query)
                if block:
                    results['blocks'].append(block.to_dict())
            
            # Check if query is a transaction ID
            if len(query) == 64:  # Assuming SHA-256 hash
                transaction = self.get_transaction(query)
                if transaction:
                    results['transactions'].append(transaction.to_dict())
            
            # Check if query is an address
            if query.startswith('porw1'):
                address = self.get_address(query)
                if address:
                    results['addresses'].append(address.to_dict())
            
            # Search for proteins
            proteins = self.database.search_proteins(query, limit=5)
            for protein_data in proteins:
                protein = self._convert_to_protein_summary(protein_data)
                results['proteins'].append(protein.to_dict())
            
            # Search for storage nodes
            nodes = self.database.search_storage_nodes(query, limit=5)
            for node_data in nodes:
                node = self._convert_to_storage_node_summary(node_data)
                results['storage_nodes'].append(node.to_dict())
            
            return results
        except Exception as e:
            logger.error(f"Error searching for {query}: {e}")
            return {
                'blocks': [],
                'transactions': [],
                'addresses': [],
                'proteins': [],
                'storage_nodes': []
            }

    def _convert_to_block_summary(self, block_data: Dict[str, Any]) -> BlockSummary:
        """
        Convert block data to BlockSummary.

        Args:
            block_data: Block data from database

        Returns:
            BlockSummary
        """
        return BlockSummary(
            height=block_data['height'],
            hash=block_data['hash'],
            timestamp=block_data['timestamp'],
            transaction_count=block_data.get('transaction_count', 0),
            size=block_data.get('size', 0),
            block_type=block_data.get('block_type', 'PoRW'),
            creator=block_data.get('creator', '')
        )

    def _convert_to_block_detail(self, block_data: Dict[str, Any]) -> BlockDetail:
        """
        Convert block data to BlockDetail.

        Args:
            block_data: Block data from database

        Returns:
            BlockDetail
        """
        # Get transactions
        transactions = []
        if 'transactions' in block_data:
            transactions = [
                self._convert_to_transaction_summary(tx_data)
                for tx_data in block_data['transactions']
            ]
        
        return BlockDetail(
            height=block_data['height'],
            hash=block_data['hash'],
            timestamp=block_data['timestamp'],
            transaction_count=block_data.get('transaction_count', 0),
            size=block_data.get('size', 0),
            block_type=block_data.get('block_type', 'PoRW'),
            creator=block_data.get('creator', ''),
            previous_hash=block_data.get('previous_hash', ''),
            merkle_root=block_data.get('merkle_root', ''),
            nonce=block_data.get('nonce', 0),
            difficulty=block_data.get('difficulty', 0),
            version=block_data.get('version', 1),
            transactions=transactions,
            porw_data=block_data.get('porw_data'),
            pors_data=block_data.get('pors_data')
        )

    def _convert_to_transaction_summary(self, tx_data: Dict[str, Any]) -> TransactionSummary:
        """
        Convert transaction data to TransactionSummary.

        Args:
            tx_data: Transaction data from database

        Returns:
            TransactionSummary
        """
        return TransactionSummary(
            id=tx_data['id'],
            block_height=tx_data.get('block_height'),
            block_hash=tx_data.get('block_hash'),
            timestamp=tx_data['timestamp'],
            sender=tx_data['sender'],
            recipient=tx_data['recipient'],
            amount=tx_data['amount'],
            fee=tx_data['fee'],
            status=tx_data.get('status', 'confirmed')
        )

    def _convert_to_transaction_detail(self, tx_data: Dict[str, Any]) -> TransactionDetail:
        """
        Convert transaction data to TransactionDetail.

        Args:
            tx_data: Transaction data from database

        Returns:
            TransactionDetail
        """
        return TransactionDetail(
            id=tx_data['id'],
            block_height=tx_data.get('block_height'),
            block_hash=tx_data.get('block_hash'),
            timestamp=tx_data['timestamp'],
            sender=tx_data['sender'],
            recipient=tx_data['recipient'],
            amount=tx_data['amount'],
            fee=tx_data['fee'],
            status=tx_data.get('status', 'confirmed'),
            nonce=tx_data.get('nonce', 0),
            memo=tx_data.get('memo'),
            is_memo_encrypted=tx_data.get('is_memo_encrypted', False),
            confirmations=tx_data.get('confirmations', 0),
            type=tx_data.get('type', 'regular'),
            contract_data=tx_data.get('contract_data'),
            confidential_data=tx_data.get('confidential_data')
        )

    def _convert_to_address_detail(self, address_data: Dict[str, Any], transactions: List[TransactionSummary]) -> AddressDetail:
        """
        Convert address data to AddressDetail.

        Args:
            address_data: Address data from database
            transactions: Recent transactions for the address

        Returns:
            AddressDetail
        """
        return AddressDetail(
            address=address_data['address'],
            balance=address_data['balance'],
            transaction_count=address_data.get('transaction_count', 0),
            first_seen=address_data.get('first_seen'),
            last_seen=address_data.get('last_seen'),
            sent_amount=address_data.get('sent_amount', 0),
            received_amount=address_data.get('received_amount', 0),
            transactions=transactions,
            is_contract=address_data.get('is_contract', False),
            contract_data=address_data.get('contract_data')
        )

    def _convert_to_protein_summary(self, protein_data: Dict[str, Any]) -> ProteinSummary:
        """
        Convert protein data to ProteinSummary.

        Args:
            protein_data: Protein data from database

        Returns:
            ProteinSummary
        """
        return ProteinSummary(
            id=protein_data['id'],
            name=protein_data['name'],
            energy_score=protein_data.get('energy_score', 0),
            folding_timestamp=protein_data.get('folding_timestamp', 0),
            scientific_value=protein_data.get('scientific_value', 0)
        )

    def _convert_to_protein_detail(self, protein_data: Dict[str, Any]) -> ProteinDetail:
        """
        Convert protein data to ProteinDetail.

        Args:
            protein_data: Protein data from database

        Returns:
            ProteinDetail
        """
        return ProteinDetail(
            id=protein_data['id'],
            name=protein_data['name'],
            energy_score=protein_data.get('energy_score', 0),
            folding_timestamp=protein_data.get('folding_timestamp', 0),
            scientific_value=protein_data.get('scientific_value', 0),
            sequence=protein_data.get('sequence', ''),
            structure=protein_data.get('structure'),
            folding_method=protein_data.get('folding_method'),
            scientific_value_details=protein_data.get('scientific_value_details'),
            references=protein_data.get('references', []),
            metadata=protein_data.get('metadata')
        )

    def _convert_to_storage_node_summary(self, node_data: Dict[str, Any]) -> StorageNodeSummary:
        """
        Convert storage node data to StorageNodeSummary.

        Args:
            node_data: Storage node data from database

        Returns:
            StorageNodeSummary
        """
        return StorageNodeSummary(
            id=node_data['id'],
            address=node_data['address'],
            status=node_data.get('status', 'offline'),
            capacity=node_data.get('capacity', 0),
            used=node_data.get('used', 0),
            reliability=node_data.get('reliability', 0),
            last_seen=node_data.get('last_seen', 0)
        )

    def _convert_to_storage_node_detail(self, node_data: Dict[str, Any]) -> StorageNodeDetail:
        """
        Convert storage node data to StorageNodeDetail.

        Args:
            node_data: Storage node data from database

        Returns:
            StorageNodeDetail
        """
        return StorageNodeDetail(
            id=node_data['id'],
            address=node_data['address'],
            status=node_data.get('status', 'offline'),
            capacity=node_data.get('capacity', 0),
            used=node_data.get('used', 0),
            reliability=node_data.get('reliability', 0),
            last_seen=node_data.get('last_seen', 0),
            version=node_data.get('version', ''),
            uptime=node_data.get('uptime', 0),
            location=node_data.get('location'),
            stored_data=node_data.get('stored_data', []),
            rewards=node_data.get('rewards')
        )


def create_explorer_api(blockchain: Blockchain, database: Database) -> ExplorerAPI:
    """
    Create an explorer API instance.

    Args:
        blockchain: Blockchain instance
        database: Database instance

    Returns:
        ExplorerAPI instance
    """
    return ExplorerAPI(blockchain, database)
