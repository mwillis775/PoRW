# src/porw_blockchain/core/consensus.py
"""
Handles the consensus mechanism logic for the hybrid PoRW/PoRS blockchain.

Includes validation rules for transactions, PoRW blocks (including time-adjusted
minting rewards), and PoRS blocks (including transaction processing and storage proofs).
"""

import datetime
import logging
import math
from typing import List, Any, Optional, Tuple

from sqlalchemy.orm import Session

# Core blockchain structures
from .structures import Transaction, PoRWBlock, PoRSBlock, AnyBlock

# Utilities and dependent modules
from . import validation as core_validation
from . import crypto_utils
from . import protein_folding # Placeholder for actual PoRW work validation
from ..storage import crud # For database interactions (fetching blocks/state)

logger = logging.getLogger(__name__)

# --- Consensus Parameters (Placeholders/Examples) ---

# PoRW Monetary Policy
TARGET_ANNUAL_INFLATION_RATE = 0.02  # Target 2% annual inflation
# Base reward can be adjusted dynamically, this is just an initial value
INITIAL_PORW_BASE_REWARD = 100.0
SECONDS_PER_YEAR = 365.25 * 24 * 60 * 60
# Time constant for reward adjustment (e.g., how quickly reward increases with time)
# Needs careful calibration based on expected discovery rate. Example: 1 day
REWARD_TIME_CONSTANT_SECONDS = 24 * 60 * 60

# PoRS Parameters
PORS_EXPECTED_INTERVAL = datetime.timedelta(minutes=5) # Example: PoRS blocks every 5 mins
PORS_QUORUM_THRESHOLD = 2/3 # Example: 2 out of 3 nodes needed for quorum

# General Validation Parameters
MAX_CLOCK_SKEW = datetime.timedelta(minutes=2) # Max allowed diff between node time and block time


# === Transaction Validation ===

def validate_transaction(transaction: Transaction, db: Session) -> bool:
    """
    Validates a single transaction based on signature and sender balance.

    Args:
        transaction: The Transaction object to validate.
        db: The SQLAlchemy database session for balance checking.

    Returns:
        True if the transaction is valid, False otherwise.
    """
    try:
        # 1. Verify the cryptographic signature
        if not transaction.signature:
            logger.warning(f"Tx {transaction.transaction_id[:8]} validation failed: Missing signature.")
            return False

        # Get public key bytes (assuming sender address IS the public key PEM for now)
        # TODO: Implement proper address-to-pubkey resolution if needed
        try:
            public_key_pem = transaction.sender.encode('utf-8') # Placeholder assumption
            message_bytes = transaction.get_signing_data()
            signature_bytes = bytes.fromhex(transaction.signature) # Assuming hex encoded signature

            if not crypto_utils.verify_signature(public_key_pem, signature_bytes, message_bytes):
                logger.warning(f"Tx {transaction.transaction_id[:8]} validation failed: Invalid signature.")
                return False
        except Exception as e:
             logger.error(f"Tx {transaction.transaction_id[:8]} signature verification error: {e}", exc_info=True)
             return False

        # 2. Check that the sender has sufficient balance (Placeholder)
        # TODO: Replace placeholder get_balance with real implementation
        sender_balance = crypto_utils.get_balance(transaction.sender, db) # Pass db session
        if transaction.amount > sender_balance:
            logger.warning(f"Tx {transaction.transaction_id[:8]} validation failed: Insufficient balance "
                           f"(Need {transaction.amount}, Have {sender_balance}) for sender {transaction.sender}.")
            return False

        # 3. Ensure the amount is positive (already handled by Pydantic model `gt=0`)
        # if transaction.amount <= 0:
        #     logger.warning(f"Tx {transaction.transaction_id[:8]} validation failed: Non-positive amount.")
        #     return False

        logger.debug(f"Transaction {transaction.transaction_id[:8]} validation passed.")
        return True

    except Exception as e:
        logger.error(f"Error during transaction validation for {transaction.transaction_id[:8]}: {e}", exc_info=True)
        return False


# === PoRW Specific Consensus Logic ===

def calculate_porw_reward(time_since_last_porw: datetime.timedelta) -> float:
    """
    Calculates the PoRW minting reward based on the time elapsed since the
    last PoRW block, aiming for the target annual inflation rate.

    Args:
        time_since_last_porw: Timedelta since the last PoRW block was created.

    Returns:
        The calculated minting reward for the new PoRW block.
    """
    # Simple exponential increase model - needs careful tuning!
    # Reward = Base * exp(time_delta / time_constant)
    # This is a placeholder model. A more sophisticated model would consider
    # the total supply and target inflation directly.
    time_delta_seconds = time_since_last_porw.total_seconds()

    # Avoid excessively large rewards if the gap is huge (e.g., chain start)
    # Cap the effective time delta used for calculation if necessary
    max_reasonable_delta = REWARD_TIME_CONSTANT_SECONDS * 10 # Example cap
    effective_delta = min(time_delta_seconds, max_reasonable_delta)

    # Calculate reward multiplier (increases as time delta grows)
    reward_multiplier = math.exp(effective_delta / REWARD_TIME_CONSTANT_SECONDS)

    calculated_reward = INITIAL_PORW_BASE_REWARD * reward_multiplier

    # TODO: Implement a more robust monetary policy that directly targets
    # the 2% inflation based on current total supply. This current model
    # is a simplified placeholder showing time-adjustment.

    logger.info(f"Calculated PoRW reward: {calculated_reward:.4f} "
                f"(Time since last: {time_since_last_porw}, Multiplier: {reward_multiplier:.4f})")
    return calculated_reward


def validate_porw_proof(block: PoRWBlock) -> bool:
    """
    Validates the 'Real Work' proof submitted in a PoRW block.

    Placeholder: Needs actual logic to verify the protein folding results
    or other scientific computation based on `block.porw_proof`.

    Args:
        block: The PoRWBlock to validate.

    Returns:
        True if the proof is considered valid, False otherwise.
    """
    logger.warning(f"PoRW proof validation for block {block.index} is using PLACEHOLDER logic.")
    # --- Placeholder Logic ---
    # 1. Check if porw_proof field has expected structure/data.
    # 2. Call protein_folding.evaluate_folding_result(block.porw_proof) -> bool
    # 3. Check if the result meets minimum quality/novelty criteria.
    # --- End Placeholder ---
    if block.porw_proof is not None: # Basic check
        logger.debug(f"PoRW proof for block {block.index} passed placeholder validation.")
        return True
    else:
        logger.warning(f"PoRW proof validation FAILED for block {block.index}: Proof data missing.")
        return False


def validate_porw_block_specifics(block: PoRWBlock, db: Session) -> bool:
    """
    Performs validation checks specific to PoRW blocks.

    Args:
        block: The PoRWBlock object to validate.
        db: The SQLAlchemy database session.

    Returns:
        True if the PoRW-specific checks pass, False otherwise.
    """
    # 1. Validate the PoRW Proof itself
    if not validate_porw_proof(block):
        logger.warning(f"PoRW block {block.index} failed: Invalid PoRW proof.")
        return False

    # 2. Validate the Minted Amount
    last_porw_block_db = crud.get_latest_block_by_type(db, block_type="PoRW", before_index=block.index)
    if last_porw_block_db:
        time_since_last = block.timestamp - last_porw_block_db.timestamp
    else:
        # If this is the first PoRW block, use a default interval or reward?
        # For simplicity, assume a default large interval leading to base reward? Or handle genesis differently.
        # Let's assume the first PoRW block gets the base reward.
        time_since_last = datetime.timedelta(seconds=REWARD_TIME_CONSTANT_SECONDS) # Leads to multiplier=e
        logger.info(f"Block {block.index} appears to be the first PoRW block, using default time delta for reward calc.")
        # A better approach might be to check if index 0 is PoRW and handle genesis explicitly

    expected_reward = calculate_porw_reward(time_since_last)
    # Allow for small floating point tolerance
    if not math.isclose(block.minted_amount, expected_reward, rel_tol=1e-7):
        logger.warning(f"PoRW block {block.index} failed: Incorrect minted amount. "
                       f"Got {block.minted_amount}, Expected {expected_reward}")
        return False

    # 3. Validate Protein Data Reference (Basic check)
    if not block.protein_data_ref or len(block.protein_data_ref) < 5: # Example basic check
        logger.warning(f"PoRW block {block.index} failed: Invalid protein_data_ref.")
        return False

    # 4. Ensure no user transactions are present (as per design)
    # This check depends on how blocks are constructed/received. If using Pydantic models,
    # the model structure itself prevents user txs. If handling raw data, add check here.

    logger.debug(f"PoRW block {block.index} specific validations passed.")
    return True


# === PoRS Specific Consensus Logic ===

def validate_pors_proof(block: PoRSBlock) -> bool:
    """
    Validates the Proof of Reliable Storage proof submitted in a PoRS block.

    Placeholder: Needs actual logic to verify quorum signatures, challenge/response data, etc.
    This will likely involve interaction with the P2P layer and node state.

    Args:
        block: The PoRSBlock to validate.

    Returns:
        True if the PoRS proof is considered valid, False otherwise.
    """
    logger.warning(f"PoRS proof validation for block {block.index} is using PLACEHOLDER logic.")
    # --- Placeholder Logic ---
    # 1. Check if pors_proof field has expected structure (e.g., quorum_id, signatures).
    # 2. Query node state/P2P layer for details about the claimed quorum_id.
    # 3. Verify signatures from participating nodes against the challenge data.
    # 4. Check if the number of valid signatures meets PORS_QUORUM_THRESHOLD.
    # --- End Placeholder ---
    if isinstance(block.pors_proof, dict) and "result" in block.pors_proof: # Basic check
        logger.debug(f"PoRS proof for block {block.index} passed placeholder validation.")
        return True
    else:
        logger.warning(f"PoRS proof validation FAILED for block {block.index}: Proof data invalid/missing.")
        return False


def validate_pors_block_specifics(block: PoRSBlock, db: Session) -> bool:
    """
    Performs validation checks specific to PoRS blocks.

    Args:
        block: The PoRSBlock object to validate.
        db: The SQLAlchemy database session for transaction validation.

    Returns:
        True if the PoRS-specific checks pass, False otherwise.
    """
    # 1. Validate the PoRS Proof itself
    if not validate_pors_proof(block):
        logger.warning(f"PoRS block {block.index} failed: Invalid PoRS proof.")
        return False

    # 2. Validate all included transactions
    if not block.transactions:
         logger.warning(f"PoRS block {block.index} validation failed: Block contains no transactions.")
         # Decide if empty PoRS blocks are allowed by protocol rules
         # return False # Uncomment if empty PoRS blocks are invalid

    for tx in block.transactions:
        if not validate_transaction(tx, db):
            logger.warning(f"PoRS block {block.index} failed: Contains invalid transaction {tx.transaction_id[:8]}.")
            return False

    # 3. Validate storage rewards (if present) - Placeholder
    if block.storage_rewards:
        # TODO: Add logic to check if rewards are correctly calculated/distributed
        # based on pors_proof results and node participation.
        logger.debug(f"PoRS block {block.index} storage rewards present (validation pending).")
        pass

    # 4. Check block interval (optional, informational)
    # This might be useful but strict enforcement could be complex with network latency
    # last_pors_block = crud.get_latest_block_by_type(db, "PoRS", before_index=block.index)
    # if last_pors_block:
    #     interval = block.timestamp - last_pors_block.timestamp
    #     if not (PORS_EXPECTED_INTERVAL * 0.8 <= interval <= PORS_EXPECTED_INTERVAL * 1.2): # Allow some variance
    #         logger.warning(f"PoRS block {block.index} interval {interval} deviates significantly from expected {PORS_EXPECTED_INTERVAL}.")


    logger.debug(f"PoRS block {block.index} specific validations passed.")
    return True


# === Overall Block Consensus Validation ===

def validate_block_for_consensus(block: AnyBlock, db: Session) -> bool:
    """
    Performs comprehensive validation checks required for consensus before
    accepting any block (PoRW or PoRS). Orchestrator function.

    Args:
        block: The block (PoRWBlock or PoRSBlock) to validate.
        db: The SQLAlchemy database session.

    Returns:
        True if the block passes all consensus checks, False otherwise.
    """
    logger.info(f"Starting consensus validation for block index {block.index} (Type: {block.block_type})...")

    # 1. Basic Structure and Hash Validation (using core validation)
    # Ensure hash calculation matches content
    if not block.block_hash or block.calculate_hash() != block.block_hash:
         logger.warning(f"Consensus failed for block {block.index}: Invalid block hash.")
         return False
    logger.debug(f"Block {block.index} hash integrity check passed.")

    # 2. Check Block Linkage (Previous Hash)
    if block.index > 0: # Genesis block has no previous block to check against
        previous_block_db = crud.get_db_block_by_index(db, block.index - 1)
        if previous_block_db is None:
            logger.warning(f"Consensus failed for block {block.index}: Previous block (index {block.index - 1}) not found.")
            return False
        if previous_block_db.block_hash != block.previous_hash:
            logger.warning(f"Consensus failed for block {block.index}: Previous hash mismatch. "
                           f"Expected {previous_block_db.block_hash}, Got {block.previous_hash}")
            return False
        logger.debug(f"Block {block.index} linkage (previous hash) check passed.")
    elif block.previous_hash != "0" * 64: # Genesis block specific check
         logger.warning(f"Consensus failed for Genesis block {block.index}: Previous hash is not all zeros.")
         return False
    else:
         logger.debug(f"Block {block.index} is Genesis block, previous hash check skipped/passed.")


    # 3. Check Timestamp Validity
    current_time_utc = datetime.datetime.now(datetime.timezone.utc)
    if block.timestamp > current_time_utc + MAX_CLOCK_SKEW:
        logger.warning(f"Consensus failed for block {block.index}: Timestamp ({block.timestamp}) is too far in the future.")
        return False
    # Optional: Check if timestamp is reasonably after the previous block's timestamp
    if block.index > 0 and previous_block_db and block.timestamp <= previous_block_db.timestamp:
         logger.warning(f"Consensus failed for block {block.index}: Timestamp ({block.timestamp}) is not after previous block ({previous_block_db.timestamp}).")
         return False
    logger.debug(f"Block {block.index} timestamp check passed.")


    # 4. Call Type-Specific Validation Logic
    validation_passed = False
    if block.block_type == "PoRW":
        # Ensure it's a PoRWBlock instance for type safety if needed, though Pydantic handles it
        if isinstance(block, PoRWBlock):
            validation_passed = validate_porw_block_specifics(block, db)
        else:
             logger.error(f"Type mismatch during PoRW validation for block {block.index}") # Should not happen with Pydantic
             return False
    elif block.block_type == "PoRS":
         if isinstance(block, PoRSBlock):
            validation_passed = validate_pors_block_specifics(block, db)
         else:
             logger.error(f"Type mismatch during PoRS validation for block {block.index}") # Should not happen
             return False
    else:
        # Should not happen if using the defined structures
        logger.error(f"Consensus failed for block {block.index}: Unknown block type '{block.block_type}'.")
        return False

    if not validation_passed:
        logger.warning(f"Consensus FAILED for block {block.index} during type-specific checks.")
        return False

    logger.info(f"Consensus validation PASSED for block {block.index} (Type: {block.block_type}).")
    return True

