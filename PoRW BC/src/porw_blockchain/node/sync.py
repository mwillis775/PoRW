# src/porw_blockchain/node/sync.py
"""
Handles blockchain synchronization logic between nodes.

Compares local chain state with peers, requests missing blocks,
validates incoming blocks, and updates the local chain.
"""

import asyncio
import logging
from typing import Optional

from sqlalchemy.orm import Session

# Adjust imports based on final project structure
from ..storage import crud
from ..storage.database import get_db_session # Or pass session differently
from ..storage.models import DbBlock
from ..core import validation
from ..core.structures import Block as BlockSchema # Pydantic model
# Need access to P2P functions/state eventually
from . import p2p

logger = logging.getLogger(__name__)

# Basic state management placeholder
is_syncing = False


async def get_local_chain_height() -> int:
    """
    Gets the index of the latest block in the local database.

    Returns:
        The index of the latest block, or -1 if the chain is empty.
    """
    # Using context manager for session scope
    with get_db_session() as db:
        latest_block: Optional[DbBlock] = crud.get_latest_db_block(db)
        if latest_block:
            return latest_block.index
        else:
            return -1 # Indicate empty chain


async def compare_with_peers():
    """
    Periodically compares local chain height with connected peers
    and initiates synchronization if necessary.
    """
    global is_syncing
    if is_syncing:
        logger.debug("Synchronization already in progress.")
        return

    try:
        is_syncing = True
        logger.info("Starting peer comparison for synchronization...")
        local_height = await get_local_chain_height()
        logger.info(f"Local chain height: {local_height}")

        # --- Placeholder for P2P Interaction ---
        # TODO: Iterate through connected peers (from p2p.connected_peers)
        # TODO: Send a message ('GET_STATUS'?) to each peer requesting their height/latest hash
        # TODO: Handle responses from peers

        # Example placeholder logic:
        # best_peer_height = local_height
        # target_peer = None
        # for peer in p2p.connected_peers:
        #     peer_height = await request_peer_status(peer) # Needs implementation
        #     if peer_height > best_peer_height:
        #         best_peer_height = peer_height
        #         target_peer = peer

        # if target_peer:
        #     logger.info(f"Found peer {target_peer} with height {best_peer_height}. Need to sync.")
        #     await request_missing_blocks(target_peer, local_height + 1, best_peer_height)
        # else:
        #     logger.info("Local chain appears up-to-date with connected peers.")
        # --- End Placeholder ---

        logger.info("Peer comparison finished.")

    except Exception as e:
        logger.error(f"Error during peer comparison: {e}", exc_info=True)
    finally:
        is_syncing = False


async def request_missing_blocks(peer: 'p2p.Peer', start_index: int, end_index: int):
    """
    Requests a range of blocks from a specific peer. (Placeholder)
    """
    logger.info(f"Requesting blocks {start_index}-{end_index} from peer {peer.host}:{peer.port}")
    # --- Placeholder for P2P Interaction ---
    # TODO: Implement P2P message sending ('GET_BLOCKS'?)
    # TODO: Send request message(s) to the peer via p2p functions/writer object.
    # Example:
    # message = create_get_blocks_message(start_index, end_index)
    # await send_message_to_peer(peer, message) # Needs implementation in p2p.py
    # --- End Placeholder ---
    pass


async def handle_received_block(block_data: dict):
    """
    Handles a block received from a peer. Validates it and attempts to add
    it to the local chain. (Called by P2P layer when block data arrives)
    """
    global is_syncing
    logger.debug(f"Handling received block data: {block_data.get('index')}")

    try:
        # 1. Deserialize/Validate structure using Pydantic model
        # This automatically checks fields and basic types
        try:
            block = BlockSchema(**block_data)
        except Exception as e: # Catch Pydantic validation errors
             logger.warning(f"Received block failed structure validation: {e}")
             return

        # 2. Perform Core Validation (Hash check)
        if not validation.validate_block_hash(block):
            logger.warning(f"Received block {block.index} failed hash validation.")
            return

        # 3. Check Linkage & Consensus Rules (More complex logic needed here)
        with get_db_session() as db:
            latest_local_block = crud.get_latest_db_block(db)
            expected_index = -1
            expected_prev_hash = "0" * 64 # Genesis block case

            if latest_local_block:
                expected_index = latest_local_block.index + 1
                expected_prev_hash = latest_local_block.hash

            if block.index != expected_index:
                logger.warning(f"Received block {block.index} out of sequence. Expected {expected_index}.")
                # Might need more complex logic for forks/reorgs later
                return

            if block.previous_hash != expected_prev_hash:
                logger.warning(f"Received block {block.index} previous hash mismatch.")
                # Fork detected or invalid block
                return

            # TODO: Add PoRW validation call here
            # if not consensus.validate_porw(block):
            #     logger.warning(f"Received block {block.index} failed PoRW validation.")
            #     return

            # 4. Add block to database if all checks pass
            logger.info(f"Validation passed for received block {block.index}. Adding to DB.")
            # Note: create_db_block expects individual args, not the pydantic model directly yet
            crud.create_db_block(
                db=db,
                index=block.index,
                timestamp=block.timestamp,
                proof=block.proof,
                previous_hash=block.previous_hash,
                hash=block.hash, # Assuming hash is validated and correct
                # TODO: Handle transactions from block schema
            )
            logger.info(f"Successfully added block {block.index} to local chain.")

            # If we were syncing, maybe check if we need more blocks
            # if is_syncing:
            #    await check_sync_status() # Needs implementation

    except Exception as e:
        logger.error(f"Error handling received block: {e}", exc_info=True)


async def synchronization_loop(interval_seconds: int = 60):
    """
    Periodically triggers the chain synchronization process.
    """
    logger.info(f"Starting synchronization loop (interval: {interval_seconds}s)")
    while True:
        await compare_with_peers()
        await asyncio.sleep(interval_seconds)

# Usually, the synchronization_loop would be started as a background task
# by the main node application runner.