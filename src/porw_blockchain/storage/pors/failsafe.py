# src/porw_blockchain/storage/pors/failsafe.py
"""
Failsafe and data replication mechanisms for the PoRS storage system.

This module provides functionality to ensure the system can run with a minimal
number of nodes and automatically replicate data as more nodes become available.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .protocol import StorageProtocol, StorageConfig

logger = logging.getLogger(__name__)


@dataclass
class FailsafeConfig:
    """Configuration for the failsafe mechanism."""
    # Failsafe settings
    single_node_mode: bool = True  # Allow the system to run with a single storage node
    auto_replicate: bool = True  # Automatically replicate data to new nodes
    
    # Replication settings
    min_replication_factor: int = 1  # Minimum number of copies in single node mode
    target_replication_factor: int = 3  # Target number of copies when more nodes are available
    
    # Monitoring settings
    check_interval_seconds: int = 60  # How often to check for new nodes
    replication_batch_size: int = 10  # Number of chunks to replicate in one batch


class FailsafeManager:
    """
    Manages failsafe and data replication for the PoRS storage system.
    
    This class ensures that:
    1. The system can run with a minimal number of nodes (even just one)
    2. Data is automatically replicated as more nodes become available
    3. Data is eventually sharded across nodes when enough are available
    """
    
    def __init__(
        self,
        storage_protocol: StorageProtocol,
        config: FailsafeConfig
    ):
        """
        Initialize the failsafe manager.
        
        Args:
            storage_protocol: The storage protocol to manage
            config: Configuration for the failsafe mechanism
        """
        self.storage_protocol = storage_protocol
        self.config = config
        
        # State tracking
        self.running = False
        self.known_nodes: Set[str] = set()
        self.replication_queue: List[str] = []  # Chunk IDs that need replication
        self.replication_task: Optional[asyncio.Task] = None
        
        logger.info("Initialized failsafe manager")
    
    async def start(self) -> None:
        """Start the failsafe manager."""
        if self.running:
            logger.warning("Failsafe manager is already running")
            return
        
        self.running = True
        logger.info("Starting failsafe manager")
        
        # Apply single node mode if configured
        if self.config.single_node_mode:
            self._apply_single_node_mode()
        
        # Start replication task if auto-replicate is enabled
        if self.config.auto_replicate:
            self.replication_task = asyncio.create_task(self._replication_loop())
        
        logger.info("Failsafe manager started")
    
    async def stop(self) -> None:
        """Stop the failsafe manager."""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping failsafe manager")
        
        # Cancel replication task if running
        if self.replication_task:
            self.replication_task.cancel()
            try:
                await self.replication_task
            except asyncio.CancelledError:
                pass
            self.replication_task = None
        
        logger.info("Failsafe manager stopped")
    
    def _apply_single_node_mode(self) -> None:
        """Apply single node mode settings to the storage protocol."""
        logger.info("Applying single node mode")
        
        # Modify the storage protocol configuration
        self.storage_protocol.config.min_replication_factor = self.config.min_replication_factor
        
        # Log the change
        logger.info(f"Set minimum replication factor to {self.config.min_replication_factor}")
    
    async def _replication_loop(self) -> None:
        """
        Main loop for monitoring and replicating data.
        
        This loop periodically checks for:
        1. New storage nodes that have joined the network
        2. Chunks that need to be replicated to meet the target replication factor
        """
        logger.info("Starting replication loop")
        
        while self.running:
            try:
                # Check for new nodes
                await self._check_for_new_nodes()
                
                # Update replication queue
                await self._update_replication_queue()
                
                # Process replication queue
                await self._process_replication_queue()
                
                # Wait for next check
                await asyncio.sleep(self.config.check_interval_seconds)
            
            except Exception as e:
                logger.error(f"Error in replication loop: {e}")
                await asyncio.sleep(10)  # Wait a bit before retrying
    
    async def _check_for_new_nodes(self) -> None:
        """Check for new storage nodes that have joined the network."""
        # Get current nodes from the storage protocol
        current_nodes = set(self.storage_protocol.get_connected_nodes())
        
        # Find new nodes
        new_nodes = current_nodes - self.known_nodes
        
        if new_nodes:
            logger.info(f"Discovered {len(new_nodes)} new storage nodes")
            
            # Update known nodes
            self.known_nodes.update(new_nodes)
            
            # If we now have enough nodes, update the replication factor
            if len(self.known_nodes) >= self.config.target_replication_factor:
                logger.info(f"Enough nodes available, setting target replication factor to {self.config.target_replication_factor}")
                self.storage_protocol.config.min_replication_factor = self.config.target_replication_factor
    
    async def _update_replication_queue(self) -> None:
        """Update the queue of chunks that need replication."""
        # Skip if we don't have enough nodes
        if len(self.known_nodes) < self.config.target_replication_factor:
            return
        
        # Get all chunks and their current replication status
        chunks = self.storage_protocol.get_all_chunks()
        
        # Find chunks that need more replicas
        for chunk_id, replicas in chunks.items():
            if len(replicas) < self.config.target_replication_factor:
                if chunk_id not in self.replication_queue:
                    self.replication_queue.append(chunk_id)
        
        if self.replication_queue:
            logger.info(f"{len(self.replication_queue)} chunks need replication")
    
    async def _process_replication_queue(self) -> None:
        """Process the replication queue."""
        # Skip if queue is empty or we don't have enough nodes
        if not self.replication_queue or len(self.known_nodes) < 2:
            return
        
        # Process a batch of chunks
        batch_size = min(self.config.replication_batch_size, len(self.replication_queue))
        batch = self.replication_queue[:batch_size]
        
        logger.info(f"Replicating {len(batch)} chunks")
        
        # Replicate each chunk in the batch
        for chunk_id in batch:
            try:
                # Request replication from the storage protocol
                success = await self.storage_protocol.replicate_chunk(chunk_id)
                
                if success:
                    # Remove from queue if successful
                    self.replication_queue.remove(chunk_id)
                    logger.debug(f"Successfully replicated chunk {chunk_id}")
                else:
                    logger.warning(f"Failed to replicate chunk {chunk_id}")
            
            except Exception as e:
                logger.error(f"Error replicating chunk {chunk_id}: {e}")
    
    def get_status(self) -> Dict:
        """
        Get the current status of the failsafe manager.
        
        Returns:
            A dictionary with status information.
        """
        return {
            "running": self.running,
            "single_node_mode": self.config.single_node_mode,
            "auto_replicate": self.config.auto_replicate,
            "known_nodes": len(self.known_nodes),
            "replication_queue_size": len(self.replication_queue),
            "current_replication_factor": self.storage_protocol.config.min_replication_factor,
            "target_replication_factor": self.config.target_replication_factor
        }
