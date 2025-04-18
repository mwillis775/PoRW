#!/usr/bin/env python3
"""
Blockchain implementation for the PoRW blockchain.
"""

import datetime
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from .structures import PoRWBlock

logger = logging.getLogger(__name__)


class Blockchain:
    """
    Blockchain for the PoRW system.

    This class provides functionality for:
    1. Managing the blockchain
    2. Adding blocks
    3. Validating blocks
    4. Calculating balances
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the blockchain.

        Args:
            data_dir: Data directory for the blockchain
        """
        self.data_dir = data_dir or Path.home() / '.porw' / 'blockchain'
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Blockchain state
        self.blocks: List[PoRWBlock] = []
        self.height = 0
        self.difficulty = 1
        self.last_block: Optional[PoRWBlock] = None

        # Load blockchain from disk
        self._load_blockchain()

        logger.info(f"Initialized blockchain with height {self.height}")

    def _load_blockchain(self) -> None:
        """Load the blockchain from disk."""
        blocks_file = self.data_dir / 'blocks.json'

        if blocks_file.exists():
            try:
                with open(blocks_file, 'r') as f:
                    blocks_data = json.load(f)

                for block_data in blocks_data:
                    block = PoRWBlock.model_validate(block_data)
                    self.blocks.append(block)

                if self.blocks:
                    self.height = len(self.blocks)
                    self.last_block = self.blocks[-1]
                    self.difficulty = self._calculate_difficulty()

                logger.info(f"Loaded {len(self.blocks)} blocks from disk")

            except Exception as e:
                logger.error(f"Error loading blockchain: {e}")
                # Initialize with genesis block
                self._create_genesis_block()
        else:
            # Initialize with genesis block
            self._create_genesis_block()

    def _save_blockchain(self) -> None:
        """Save the blockchain to disk."""
        blocks_file = self.data_dir / 'blocks.json'

        try:
            with open(blocks_file, 'w') as f:
                blocks_data = [block.model_dump(mode='json') for block in self.blocks]
                json.dump(blocks_data, f, indent=2)

            logger.info(f"Saved {len(self.blocks)} blocks to disk")

        except Exception as e:
            logger.error(f"Error saving blockchain: {e}")

    def _create_genesis_block(self) -> None:
        """Create the genesis block."""
        # Create genesis block
        genesis_block = PoRWBlock(
            index=0,
            previous_hash="0" * 64,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            block_hash="",
            block_type="PoRW",  # Must be "PoRW" to match the Literal type
            porw_proof={
                "protein_id": "genesis",
                "amino_sequence": "GENESIS",
                "energy_score": 0.0,
                "folding_time_ms": 0,
                "method_used": "Genesis",
                "structure_hash": "0" * 64
            },
            minted_amount=100.0,
            protein_data_ref="genesis:0"
        )

        # Calculate block hash
        genesis_block.block_hash = genesis_block.calculate_hash()

        # Add to blockchain
        self.blocks.append(genesis_block)
        self.height = 1
        self.last_block = genesis_block

        # Save blockchain
        self._save_blockchain()

        logger.info("Created genesis block")

    def add_block(self, block: PoRWBlock) -> bool:
        """
        Add a block to the blockchain.

        Args:
            block: Block to add

        Returns:
            True if the block was added, False otherwise
        """
        # Validate block
        if not self.validate_block(block):
            logger.warning(f"Invalid block: {block.block_hash}")
            return False

        # Add block to blockchain
        self.blocks.append(block)
        self.height += 1
        self.last_block = block

        # Recalculate difficulty
        self.difficulty = self._calculate_difficulty()

        # Save blockchain
        self._save_blockchain()

        logger.info(f"Added block {block.index} to blockchain")

        return True

    def validate_block(self, block: PoRWBlock) -> bool:
        """
        Validate a block.

        Args:
            block: Block to validate

        Returns:
            True if the block is valid, False otherwise
        """
        # Check if block index is correct
        if block.index != self.height:
            logger.warning(f"Invalid block index: {block.index} != {self.height}")
            return False

        # Check if previous hash is correct
        if block.previous_hash != self.last_block.block_hash:
            logger.warning(f"Invalid previous hash: {block.previous_hash} != {self.last_block.block_hash}")
            return False

        # Check if block hash is correct
        if block.block_hash != block.calculate_hash():
            logger.warning(f"Invalid block hash: {block.block_hash} != {block.calculate_hash()}")
            return False

        # Check if block meets difficulty requirement
        if not self._meets_difficulty(block.block_hash):
            logger.warning(f"Block does not meet difficulty requirement: {block.block_hash}")
            return False

        # Check if block type is valid
        if block.block_type != "PoRW":  # Only allow PoRW blocks
            logger.warning(f"Invalid block type: {block.block_type}")
            return False

        # Check if PoRW proof is valid
        if block.block_type == "PoRW" and not self._validate_porw_proof(block.porw_proof):
            logger.warning(f"Invalid PoRW proof: {block.porw_proof}")
            return False

        return True

    def _calculate_difficulty(self) -> int:
        """
        Calculate the current difficulty.

        Returns:
            The current difficulty
        """
        # In a real implementation, this would adjust based on block times
        # For now, we'll just use a fixed difficulty
        return 1

    def _meets_difficulty(self, block_hash: str) -> bool:
        """
        Check if a block hash meets the difficulty requirement.

        Args:
            block_hash: Block hash to check

        Returns:
            True if the block hash meets the difficulty requirement, False otherwise
        """
        # In a real implementation, this would check if the block hash has enough leading zeros
        # For now, we'll just return True
        return True

    def _validate_porw_proof(self, porw_proof: Dict[str, Any]) -> bool:
        """
        Validate a PoRW proof.

        Args:
            porw_proof: PoRW proof to validate

        Returns:
            True if the PoRW proof is valid, False otherwise
        """
        # In a real implementation, this would validate the protein folding results
        # For now, we'll just check if the required fields are present
        required_fields = [
            "protein_id",
            "amino_sequence",
            "energy_score",
            "folding_time_ms",
            "method_used",
            "structure_hash"
        ]

        for field in required_fields:
            if field not in porw_proof:
                logger.warning(f"Missing field in PoRW proof: {field}")
                return False

        return True

    def get_balance(self, address: str) -> float:
        """
        Get the balance of an address.

        Args:
            address: Address to get balance for

        Returns:
            The balance of the address
        """
        # Calculate the balance based on minted rewards
        balance = 0.0

        # Add minted rewards from mining
        for block in self.blocks:
            if block.block_type == "PoRW" and block.porw_proof.get("miner_address") == address:
                balance += block.minted_amount

        # Add transaction amounts (not implemented yet)
        # For now, we'll add a base amount of 100.0 PORW
        balance += 100.0

        return balance

    def get_transactions(self, address: str) -> List[Dict[str, Any]]:
        """
        Get the transactions for an address.

        Args:
            address: Address to get transactions for

        Returns:
            List of transactions for the address
        """
        # In a real implementation, this would return the transactions for the address
        # For now, we'll just return an empty list
        return []
