# src/porw_blockchain/protein/mining.py
"""
Mining module for the PoRW blockchain using protein folding.

This module provides functionality to mine blocks using protein folding
as the proof of work mechanism.
"""

import asyncio
import datetime
import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Any, Tuple

from ..core.protein_folding import perform_protein_folding_simulation, FoldingResult
from ..core.structures import PoRWBlock

logger = logging.getLogger(__name__)


@dataclass
class MiningConfig:
    """Configuration for protein folding mining."""
    # Mining settings
    enable_mining: bool = True
    mining_threads: int = 4
    enable_gpu: bool = True

    # Protein data settings
    protein_data_dir: Path = None  # Will use default if None

    # Mining parameters
    target_folding_time_ms: int = 60000  # Target time for folding (1 minute)
    max_folding_attempts: int = 10  # Maximum number of folding attempts per block

    # Reward settings
    block_reward: float = 50.0  # Reward for mining a block

    def __post_init__(self):
        """Initialize default values."""
        if self.protein_data_dir is None:
            self.protein_data_dir = Path.home() / ".porw" / "protein_data"

        # Ensure protein data directory exists
        self.protein_data_dir.mkdir(parents=True, exist_ok=True)


class ProteinMiner:
    """
    Mines blocks using protein folding as the proof of work mechanism.

    This class:
    1. Selects protein sequences to fold
    2. Performs protein folding simulations
    3. Creates PoRW blocks based on the folding results
    """

    def __init__(self, config: MiningConfig):
        """
        Initialize the protein miner.

        Args:
            config: Configuration for protein folding mining
        """
        self.config = config

        # State tracking
        self.running = False
        self.mining_task: Optional[asyncio.Task] = None
        self.current_protein_id: Optional[str] = None
        self.folding_results: Dict[str, FoldingResult] = {}

        # Load protein sequences
        self.protein_sequences = self._load_protein_sequences()

        # Set up GPU if enabled
        if self.config.enable_gpu:
            self._setup_gpu()

        logger.info(f"Initialized protein miner with {len(self.protein_sequences)} protein sequences")

    async def start(self) -> None:
        """Start the protein miner."""
        if not self.config.enable_mining:
            logger.info("Mining is disabled, not starting miner")
            return

        if self.running:
            logger.warning("Protein miner is already running")
            return

        self.running = True
        logger.info("Starting protein miner")

        # Start mining task
        self.mining_task = asyncio.create_task(self._mining_loop())

        logger.info("Protein miner started")

    async def stop(self) -> None:
        """Stop the protein miner."""
        if not self.running:
            return

        self.running = False
        logger.info("Stopping protein miner")

        # Cancel mining task if running
        if self.mining_task:
            self.mining_task.cancel()
            try:
                await self.mining_task
            except asyncio.CancelledError:
                pass
            self.mining_task = None

        logger.info("Protein miner stopped")

    def _load_protein_sequences(self) -> Dict[str, str]:
        """
        Load protein sequences from the data directory.

        Returns:
            A dictionary mapping protein IDs to amino acid sequences.
        """
        sequences = {}

        # Check if protein data directory exists
        if not self.config.protein_data_dir.exists():
            logger.warning(f"Protein data directory {self.config.protein_data_dir} does not exist")
            return sequences

        # Load sequences from JSON files
        for file_path in self.config.protein_data_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)

                if "protein_id" in data and "amino_sequence" in data:
                    sequences[data["protein_id"]] = data["amino_sequence"]
            except Exception as e:
                logger.error(f"Error loading protein sequence from {file_path}: {e}")

        # If no sequences found, create some test sequences
        if not sequences:
            logger.warning("No protein sequences found, creating test sequences")
            sequences = self._create_test_sequences()

        return sequences

    def _create_test_sequences(self) -> Dict[str, str]:
        """
        Create test protein sequences for development and testing.

        Returns:
            A dictionary mapping protein IDs to amino acid sequences.
        """
        # Simple test sequences (these are just examples, not real proteins)
        test_sequences = {
            "test_protein_1": "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR",
            "test_protein_2": "MNIFEMLRIDEGLRLKIYKDTEGYYTIGIGHLLTKSPSLNAAKSELDKAIGRNTNGVITKDEAEKLFNQDVDAAVRGILRNAKLKPVYDSLDAVRRAALINMVFQMGETGVAGFTNSLRMLQQKRWDEAAVNLAKSRWYNQTPNRAKRVITTFRTGTWDAYKNL",
            "test_protein_3": "MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHQYREQIKRVKDSDDVPMVLVGNKCDLAARTVESRQAQDLARSYGIPYIETSAKTRQGVEDAFYTLVREIRQHKLRKLNPPDESGPGCMSCKCVLS"
        }

        # Save test sequences to files
        for protein_id, sequence in test_sequences.items():
            file_path = self.config.protein_data_dir / f"{protein_id}.json"
            try:
                with open(file_path, "w") as f:
                    json.dump({
                        "protein_id": protein_id,
                        "amino_sequence": sequence,
                        "description": "Test protein sequence",
                        "source": "Generated for testing"
                    }, f, indent=2)
            except Exception as e:
                logger.error(f"Error saving test sequence to {file_path}: {e}")

        return test_sequences

    def _setup_gpu(self) -> None:
        """Set up GPU for protein folding if available."""
        try:
            # This is a placeholder for actual GPU setup code
            # In a real implementation, you would set up CUDA or other GPU libraries
            logger.info("GPU support enabled for protein folding")
        except Exception as e:
            logger.warning(f"Failed to set up GPU for protein folding: {e}")
            logger.info("Falling back to CPU-only mode")
            self.config.enable_gpu = False

    async def _mining_loop(self) -> None:
        """
        Main mining loop.

        This loop:
        1. Selects a protein to fold
        2. Performs the folding simulation
        3. Creates a PoRW block if the folding is successful
        """
        logger.info("Starting mining loop")

        while self.running:
            try:
                # Select a protein to fold
                protein_id, amino_sequence = self._select_protein()

                if not protein_id:
                    logger.warning("No protein sequences available for folding")
                    await asyncio.sleep(10)
                    continue

                # Set current protein
                self.current_protein_id = protein_id

                # Perform protein folding
                logger.info(f"Mining with protein {protein_id}")
                folding_result = await self._fold_protein(protein_id, amino_sequence)

                if folding_result:
                    # Store the result
                    self.folding_results[protein_id] = folding_result

                    # Create a block
                    block = self._create_block(folding_result)

                    if block:
                        logger.info(f"Successfully mined block with protein {protein_id}")
                        # In a real implementation, you would submit this block to the network
                        # For now, we just log it
                        logger.info(f"Block: {block}")

                # Wait a bit before the next attempt
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in mining loop: {e}")
                await asyncio.sleep(10)  # Wait a bit before retrying

    def _select_protein(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Select a protein sequence to fold.

        Returns:
            A tuple of (protein_id, amino_sequence), or (None, None) if no proteins are available.
        """
        if not self.protein_sequences:
            return None, None

        # Select a random protein
        protein_id = random.choice(list(self.protein_sequences.keys()))
        amino_sequence = self.protein_sequences[protein_id]

        return protein_id, amino_sequence

    async def _fold_protein(self, protein_id: str, amino_sequence: str) -> Optional[FoldingResult]:
        """
        Perform protein folding simulation.

        Args:
            protein_id: The ID of the protein to fold
            amino_sequence: The amino acid sequence to fold

        Returns:
            The folding result, or None if folding failed.
        """
        # Set up simulation parameters
        simulation_params = {
            "temperature": 300.0,  # Kelvin
            "max_iterations": 1000,
            "force_field": "ref2015",  # Rosetta default scoring function
            "use_fragments": False,
            "use_constraints": False
        }

        # Run the simulation in a separate thread to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: perform_protein_folding_simulation(
                    protein_id, amino_sequence, simulation_params
                )
            )

            logger.info(f"Folding completed for {protein_id} with energy {result.energy_score:.2f}")
            return result

        except Exception as e:
            logger.error(f"Error folding protein {protein_id}: {e}")
            return None

    def _create_block(self, folding_result: FoldingResult) -> Optional[PoRWBlock]:
        """
        Create a PoRW block from a folding result.

        Args:
            folding_result: The result of protein folding

        Returns:
            A PoRW block, or None if block creation failed.
        """
        try:
            # In a real implementation, you would:
            # 1. Get the current blockchain state
            # 2. Select transactions from the mempool
            # 3. Create a proper block with the folding result as proof

            # Create the porw_proof data structure
            porw_proof = {
                "protein_id": folding_result.protein_id,
                "amino_sequence": folding_result.amino_sequence,
                "energy_score": folding_result.energy_score,
                "folding_time_ms": folding_result.folding_time_ms,
                "method_used": folding_result.method_used,
                "structure_hash": hashlib.sha256(str(folding_result.structure_data).encode()).hexdigest()
            }

            # Calculate minted amount based on energy score and folding time
            # Lower energy scores are better in protein folding
            # Normalize the energy score to a positive value for minting
            base_reward = 50.0  # Base reward for a successful fold
            energy_factor = 1.0 / (1.0 + abs(folding_result.energy_score))  # Higher for better (more negative) energy scores
            time_factor = 1.0 / (1.0 + (folding_result.folding_time_ms / 1000.0))  # Higher for faster folding times

            # Calculate minted amount based on quality and efficiency
            minted_amount = base_reward * (0.7 * energy_factor + 0.3 * time_factor)

            # Ensure minted amount is positive and reasonable
            minted_amount = max(1.0, min(minted_amount, 100.0))

            # Create a unique reference for the protein data
            protein_data_ref = f"protein:{folding_result.protein_id}:{hashlib.sha256(str(folding_result.structure_data).encode()).hexdigest()[:16]}"

            # Get current timestamp as a datetime object
            current_time = datetime.datetime.now(datetime.timezone.utc)

            # Create the PoRW block
            block = PoRWBlock(
                index=0,  # This would be the next block index in a real implementation
                previous_hash="0000000000000000000000000000000000000000000000000000000000000000",  # Previous block hash
                timestamp=current_time,
                block_hash="",  # Will be calculated
                block_type="PoRW",  # Explicitly set the block type
                porw_proof=porw_proof,
                minted_amount=minted_amount,
                protein_data_ref=protein_data_ref
            )

            # Calculate block hash
            block.block_hash = block.calculate_hash()

            logger.info(f"Created PoRW block with protein {folding_result.protein_id}, minted amount: {minted_amount:.2f}")
            return block

        except Exception as e:
            logger.error(f"Error creating block: {e}")
            return None

    def get_status(self) -> Dict:
        """
        Get the current status of the protein miner.

        Returns:
            A dictionary with status information.
        """
        return {
            "running": self.running,
            "enable_mining": self.config.enable_mining,
            "mining_threads": self.config.mining_threads,
            "enable_gpu": self.config.enable_gpu,
            "protein_sequences": len(self.protein_sequences),
            "current_protein_id": self.current_protein_id,
            "folding_results": len(self.folding_results)
        }
