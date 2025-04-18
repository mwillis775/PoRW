"""
PoRW Blockchain Client

This module provides the main client for interacting with the PoRW Blockchain.
"""

import json
from typing import Dict, List, Optional, Any, Union

import requests

from .types import (
    BlockchainInfo,
    Block,
    Transaction,
    NetworkStats,
    TransactionReceipt,
    ProteinData,
    StorageNodeInfo,
)


class PoRWClientError(Exception):
    """Exception raised for PoRW client errors."""

    pass


class PoRWClient:
    """Client for interacting with the PoRW Blockchain."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        testnet: bool = False,
    ):
        """
        Initialize the PoRW Blockchain client.

        Args:
            base_url: Base URL of the PoRW Blockchain node
            api_key: API key for authentication (if required)
            timeout: Timeout for API requests in seconds
            testnet: Whether to use testnet
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.testnet = testnet
        self.session = requests.Session()

        # Set up headers
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["X-API-Key"] = api_key

    def _request(
        self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None
    ) -> Dict:
        """
        Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Request body data

        Returns:
            Response data

        Raises:
            PoRWClientError: If the request fails
        """
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                response = self.session.get(
                    url, params=params, headers=self.headers, timeout=self.timeout
                )
            elif method == "POST":
                response = self.session.post(
                    url,
                    params=params,
                    json=data,
                    headers=self.headers,
                    timeout=self.timeout,
                )
            else:
                raise PoRWClientError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            result = response.json()

            if not result.get("success", False):
                raise PoRWClientError(result.get("error", "Unknown error"))

            return result.get("data", {})
        except requests.exceptions.RequestException as e:
            raise PoRWClientError(f"Request failed: {str(e)}")
        except json.JSONDecodeError:
            raise PoRWClientError("Invalid JSON response")

    def get_blockchain_info(self) -> BlockchainInfo:
        """
        Get information about the blockchain.

        Returns:
            Blockchain information
        """
        return self._request("GET", "/api/blockchain/info")

    def get_block_by_height(self, height: int) -> Block:
        """
        Get a block by its height.

        Args:
            height: Block height

        Returns:
            Block data
        """
        return self._request("GET", f"/api/blocks/height/{height}")

    def get_block_by_hash(self, hash: str) -> Block:
        """
        Get a block by its hash.

        Args:
            hash: Block hash

        Returns:
            Block data
        """
        return self._request("GET", f"/api/blocks/hash/{hash}")

    def get_latest_blocks(self, limit: int = 10) -> List[Block]:
        """
        Get the latest blocks.

        Args:
            limit: Maximum number of blocks to return (default: 10)

        Returns:
            Array of blocks
        """
        return self._request("GET", f"/api/blocks/latest", params={"limit": limit})

    def get_transaction(self, tx_id: str) -> Transaction:
        """
        Get a transaction by its ID.

        Args:
            tx_id: Transaction ID

        Returns:
            Transaction data
        """
        return self._request("GET", f"/api/transactions/{tx_id}")

    def get_transactions_for_address(
        self, address: str, limit: int = 50, offset: int = 0
    ) -> List[Transaction]:
        """
        Get transactions for an address.

        Args:
            address: Wallet address
            limit: Maximum number of transactions to return (default: 50)
            offset: Offset for pagination (default: 0)

        Returns:
            Array of transactions
        """
        return self._request(
            "GET",
            f"/api/addresses/{address}/transactions",
            params={"limit": limit, "offset": offset},
        )

    def get_balance(self, address: str) -> float:
        """
        Get the balance for an address.

        Args:
            address: Wallet address

        Returns:
            Balance in PoRW tokens
        """
        result = self._request("GET", f"/api/addresses/{address}/balance")
        return result.get("balance", 0.0)

    def submit_transaction(self, raw_transaction: Dict) -> TransactionReceipt:
        """
        Submit a raw transaction to the network.

        Args:
            raw_transaction: Signed transaction data

        Returns:
            Transaction receipt
        """
        return self._request("POST", "/api/transactions/submit", data=raw_transaction)

    def get_network_stats(self) -> NetworkStats:
        """
        Get network statistics.

        Returns:
            Network statistics
        """
        return self._request("GET", "/api/network/stats")

    def get_protein_folding_data(self, protein_id: str) -> ProteinData:
        """
        Get protein folding data.

        Args:
            protein_id: Protein ID

        Returns:
            Protein data
        """
        return self._request("GET", f"/api/proteins/{protein_id}")

    def get_available_proteins(self, limit: int = 50, offset: int = 0) -> List[ProteinData]:
        """
        Get a list of available proteins.

        Args:
            limit: Maximum number of proteins to return (default: 50)
            offset: Offset for pagination (default: 0)

        Returns:
            Array of protein IDs and metadata
        """
        return self._request(
            "GET", "/api/proteins", params={"limit": limit, "offset": offset}
        )

    def get_storage_nodes(self, limit: int = 50, offset: int = 0) -> List[StorageNodeInfo]:
        """
        Get information about storage nodes.

        Args:
            limit: Maximum number of nodes to return (default: 50)
            offset: Offset for pagination (default: 0)

        Returns:
            Array of storage node information
        """
        return self._request(
            "GET", "/api/storage/nodes", params={"limit": limit, "offset": offset}
        )

    def get_transaction_fee_estimate(
        self, priority: str = "medium"
    ) -> float:
        """
        Get the estimated transaction fee.

        Args:
            priority: Transaction priority ('low', 'medium', or 'high')

        Returns:
            Estimated fee in PoRW tokens
        """
        result = self._request(
            "GET", "/api/transactions/fee-estimate", params={"priority": priority}
        )
        return result.get("fee", 0.0)
