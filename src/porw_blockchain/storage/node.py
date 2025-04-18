#!/usr/bin/env python3
"""
Storage node implementation for the PoRW blockchain.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..core.blockchain import Blockchain
from ..core.wallet import Wallet

logger = logging.getLogger(__name__)


class StorageNode:
    """
    Storage node for the PoRW blockchain.

    This class provides functionality for:
    1. Storing protein folding data
    2. Providing access to stored data
    3. Receiving rewards for storage
    """

    def __init__(
        self,
        wallet: Wallet,
        blockchain: Optional[Blockchain] = None,
        data_dir: Optional[Path] = None
    ):
        """
        Initialize the storage node.

        Args:
            wallet: Wallet to receive storage rewards
            blockchain: Blockchain instance
            data_dir: Data directory for the storage node
        """
        self.wallet = wallet
        self.blockchain = blockchain or Blockchain(data_dir)
        self.data_dir = data_dir or Path.home() / '.porw' / 'storage'
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Storage state
        self.running = False
        self.start_time = None
        self.stored_data = {}
        self.storage_task = None

        logger.info(f"Initialized storage node for wallet {wallet.address}")

    async def start(self) -> None:
        """Start the storage node."""
        if self.running:
            logger.warning("Storage node is already running")
            return

        self.running = True
        self.start_time = time.strftime("%Y-%m-%d %H:%M:%S")
        logger.info("Starting storage node")

        # Start storage in the background
        self.storage_task = asyncio.create_task(self._process_storage())

        logger.info("Storage node started")

    async def stop(self) -> None:
        """Stop the storage node."""
        if not self.running:
            return

        self.running = False
        logger.info("Stopping storage node")

        # Cancel storage task
        if self.storage_task:
            self.storage_task.cancel()
            try:
                await self.storage_task
            except asyncio.CancelledError:
                pass
            self.storage_task = None

        logger.info("Storage node stopped")

    async def _process_storage(self) -> None:
        """Process storage in the background."""
        while self.running:
            try:
                # Check for new blocks with protein data
                await self._check_for_new_data()

                # Sleep for a bit
                await asyncio.sleep(10)

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"Error processing storage: {e}")
                await asyncio.sleep(5)

    async def _check_for_new_data(self) -> None:
        """Check for new protein data in the blockchain."""
        # In a real implementation, this would check for new blocks with protein data
        # For now, we'll just simulate storage

        # Get all blocks
        blocks = self.blockchain.blocks

        # Check for new protein data
        for block in blocks:
            if block.block_type == "PoRW" and block.protein_data_ref:
                if block.protein_data_ref not in self.stored_data:
                    # Store the protein data
                    self.stored_data[block.protein_data_ref] = {
                        "protein_id": block.porw_proof["protein_id"],
                        "amino_sequence": block.porw_proof["amino_sequence"],
                        "energy_score": block.porw_proof["energy_score"],
                        "folding_time_ms": block.porw_proof["folding_time_ms"],
                        "method_used": block.porw_proof["method_used"],
                        "structure_hash": block.porw_proof["structure_hash"],
                        "block_index": block.index,
                        "block_hash": block.block_hash,
                        "timestamp": block.timestamp
                    }

                    # Save the protein data to disk
                    await self._save_protein_data(block.protein_data_ref, self.stored_data[block.protein_data_ref])

                    logger.info(f"Stored protein data {block.protein_data_ref} from block {block.index}")

    async def _save_protein_data(self, data_ref: str, data: Dict[str, Any]) -> None:
        """
        Save protein data to disk.

        Args:
            data_ref: Reference to the protein data
            data: Protein data to save
        """
        # Create a file for the protein data
        file_path = self.data_dir / f"{data_ref.replace(':', '_')}.json"

        # Convert timestamp to string if it's a datetime object
        if 'timestamp' in data and not isinstance(data['timestamp'], (int, str)):
            data = data.copy()
            data['timestamp'] = int(data['timestamp'].timestamp())

        # Save the protein data
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def get_protein_data(self, data_ref: str) -> Optional[Dict[str, Any]]:
        """
        Get protein data by reference.

        Args:
            data_ref: Reference to the protein data

        Returns:
            The protein data, or None if not found
        """
        return self.stored_data.get(data_ref)

    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the storage node.

        Returns:
            A dictionary with status information
        """
        return {
            "running": self.running,
            "wallet": self.wallet.address,
            "stored_data_count": len(self.stored_data),
            "storage_size": self._get_storage_size(),
            "start_time": self.start_time
        }

    def _get_storage_size(self) -> int:
        """
        Get the size of the storage directory.

        Returns:
            The size of the storage directory in bytes
        """
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(self.data_dir):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                total_size += os.path.getsize(file_path)

        return total_size
