#!/usr/bin/env python3
"""
Mining node implementation for the PoRW blockchain.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..core.blockchain import Blockchain
from ..core.structures import PoRWBlock
from ..core.wallet import Wallet

logger = logging.getLogger(__name__)


class MiningNode:
    """
    Mining node for the PoRW blockchain.

    This class provides functionality for:
    1. Mining new blocks using protein folding as proof of work
    2. Submitting mined blocks to the blockchain
    3. Receiving rewards for mining
    """

    def __init__(
        self,
        wallet: Wallet,
        blockchain: Optional[Blockchain] = None,
        data_dir: Optional[Path] = None
    ):
        """
        Initialize the mining node.

        Args:
            wallet: Wallet to receive mining rewards
            blockchain: Blockchain instance
            data_dir: Data directory for the mining node
        """
        self.wallet = wallet
        self.blockchain = blockchain or Blockchain(data_dir)
        self.data_dir = data_dir or Path.home() / '.porw' / 'mining'
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Mining state
        self.running = False
        self.mining_task = None

        logger.info(f"Initialized mining node for wallet {wallet.address}")

    async def start(self) -> None:
        """Start the mining node."""
        if self.running:
            logger.warning("Mining node is already running")
            return

        self.running = True
        logger.info("Starting mining node")

        # Start mining in the background
        self.mining_task = asyncio.create_task(self._mine_blocks())

        logger.info("Mining node started")

    async def stop(self) -> None:
        """Stop the mining node."""
        if not self.running:
            return

        self.running = False
        logger.info("Stopping mining node")

        # Cancel mining task
        if self.mining_task:
            self.mining_task.cancel()
            try:
                await self.mining_task
            except asyncio.CancelledError:
                pass
            self.mining_task = None

        logger.info("Mining node stopped")

    async def _mine_blocks(self) -> None:
        """Mine blocks in the background."""
        while self.running:
            try:
                # Mine a block
                block = await self._mine_block()

                # Add block to blockchain
                if block and self.blockchain.add_block(block):
                    logger.info(f"Mined block {block.index} with hash {block.block_hash}")
                    logger.info(f"Minted {block.minted_amount} PORW for wallet {self.wallet.address}")

                    # Log the updated blockchain height
                    logger.info(f"Blockchain height: {self.blockchain.height}")

                # Sleep for a bit (shorter time for demo purposes)
                await asyncio.sleep(5)  # Mine blocks more frequently

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"Error mining block: {e}")
                await asyncio.sleep(5)

    async def _mine_block(self) -> Optional[PoRWBlock]:
        """
        Mine a block using protein folding as proof of work.

        Returns:
            The mined block, or None if mining failed
        """
        # In a real implementation, this would use a protein folding library
        # For now, we'll just simulate mining

        # Get the last block
        last_block = self.blockchain.last_block

        # Create a new block with rewards going to the wallet address
        block = PoRWBlock(
            index=self.blockchain.height,
            previous_hash=last_block.block_hash,
            timestamp=int(time.time()),
            block_hash="",
            block_type="PoRW",
            porw_proof={
                "protein_id": f"protein_{self.blockchain.height}",
                "amino_sequence": "ACDEFGHIKLMNPQRSTVWY",
                "energy_score": -100.0,
                "folding_time_ms": 1000,
                "method_used": "PyRosetta",
                "structure_hash": "0" * 64,
                "miner_address": self.wallet.address  # Add miner address to proof
            },
            minted_amount=50.0,
            protein_data_ref=f"protein_{self.blockchain.height}:0"
        )

        # Calculate block hash
        block.block_hash = block.calculate_hash()

        # Simulate mining (shorter time for demo purposes)
        await asyncio.sleep(1)  # Reduced mining time for faster results

        # Log mining success
        logger.info(f"Successfully mined block {block.index} for wallet {self.wallet.address}")

        return block

    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the mining node.

        Returns:
            A dictionary with status information
        """
        # Count mined blocks (blocks with our wallet address)
        mined_blocks = [block for block in self.blockchain.blocks
                       if block.block_type == "PoRW" and
                       block.porw_proof.get("miner_address") == self.wallet.address]

        # Calculate total minted amount
        total_minted = sum(block.minted_amount for block in mined_blocks)

        return {
            "running": self.running,
            "wallet": self.wallet.address,
            "blockchain_height": self.blockchain.height,
            "last_block_hash": self.blockchain.last_block.block_hash if self.blockchain.last_block else None,
            "mined_blocks": len(mined_blocks),
            "total_minted": total_minted
        }
