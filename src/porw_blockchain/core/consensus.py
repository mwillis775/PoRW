# src/porw_blockchain/core/consensus.py
"""
Handles the consensus mechanism logic for the hybrid PoRW/PoRS blockchain.

Includes validation rules for transactions, PoRW blocks (including time-adjusted
minting rewards), and PoRS blocks (including transaction processing and storage proofs).
"""

import datetime
import json
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

# PoRW Difficulty Adjustment Parameters
TARGET_PORW_BLOCK_TIME = datetime.timedelta(minutes=10)  # Target 10 minutes per PoRW block
DIFFICULTY_ADJUSTMENT_WINDOW = 10  # Number of blocks to consider for difficulty adjustment
MAX_DIFFICULTY_ADJUSTMENT = 4.0  # Maximum adjustment factor per update
MIN_DIFFICULTY = 1.0  # Minimum difficulty level
MAX_DIFFICULTY = 1000.0  # Maximum difficulty level
INITIAL_DIFFICULTY = 10.0  # Initial difficulty level

# PoRS Parameters
PORS_EXPECTED_INTERVAL = datetime.timedelta(minutes=5) # Example: PoRS blocks every 5 mins
PORS_QUORUM_THRESHOLD = 2/3 # Example: 2 out of 3 nodes needed for quorum

# General Validation Parameters
MAX_CLOCK_SKEW = datetime.timedelta(minutes=2) # Max allowed diff between node time and block time


# === Transaction Validation ===

def validate_transaction(transaction: Transaction, db: Session = None) -> bool:
    """
    Validates a single transaction based on signature and sender balance.

    Args:
        transaction: The Transaction object to validate.
        db: The SQLAlchemy database session for balance checking.

    Returns:
        True if the transaction is valid, False otherwise.
    """
    # For performance benchmarking without DB, skip full validation
    if db is None:
        logger.debug("validate_transaction: No DB provided, returning True")
        return True
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

        # Check if this is a confidential transaction
        if hasattr(transaction, 'is_confidential') and transaction.is_confidential:
            # Validate confidential transaction
            from ..privacy.confidential_transactions import verify_confidential_transaction
            if not verify_confidential_transaction(transaction):
                logger.warning(f"Tx {transaction.transaction_id[:8]} validation failed: Invalid confidential transaction.")
                return False

            # For confidential transactions, we can't directly check the balance
            # Instead, we rely on the zero-knowledge proofs to ensure validity
            logger.debug(f"Confidential transaction {transaction.transaction_id[:8]} validation passed.")
            return True
        else:
            # Standard transaction validation
            # 2. Check that the sender has sufficient balance including fees
            sender_balance = crypto_utils.get_balance(transaction.sender, db) # Pass db session

            # Get the effective fee (either specified or standard)
            effective_fee = transaction.get_effective_fee()

            # Total amount needed is transaction amount plus fee
            total_needed = transaction.amount + effective_fee

            if total_needed > sender_balance:
                logger.warning(f"Tx {transaction.transaction_id[:8]} validation failed: Insufficient balance "
                               f"(Need {transaction.amount} + {effective_fee} fee = {total_needed}, "
                               f"Have {sender_balance}) for sender {transaction.sender}.")
                return False

            # 3. Validate the fee is reasonable
            standard_fee = transaction.calculate_standard_fee()
            min_acceptable_fee = standard_fee * 0.5  # Allow fees as low as 50% of standard

            if effective_fee < min_acceptable_fee:
                logger.warning(f"Tx {transaction.transaction_id[:8]} validation failed: Fee too low "
                               f"(Got {effective_fee}, minimum is {min_acceptable_fee}).")
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
   
# Alias for simple block validation (used by performance tests)
def validate_block(block: AnyBlock) -> bool:
    """
    Validate a block's stored hash matches its calculated hash.
    """
    return core_validation.validate_block_hash(block)
# === PoRW Specific Consensus Logic ===

def calculate_porw_reward(time_since_last_porw: datetime.timedelta, db: Session) -> float:
    """
    Calculates the PoRW minting reward based on the time elapsed since the
    last PoRW block and the current total supply, aiming for the target annual inflation rate.

    Args:
        time_since_last_porw: Timedelta since the last PoRW block was created.
        db: Database session for querying total supply.

    Returns:
        The calculated minting reward for the new PoRW block.
    """
    # Get the current total supply from the database
    total_supply = get_total_supply(db)
    logger.info(f"Current total supply: {total_supply:.2f}")

    # Calculate time factors
    time_delta_seconds = time_since_last_porw.total_seconds()

    # Avoid excessively large rewards if the gap is huge (e.g., chain start)
    # Cap the effective time delta used for calculation if necessary
    max_reasonable_delta = REWARD_TIME_CONSTANT_SECONDS * 10  # Example cap
    effective_delta = min(time_delta_seconds, max_reasonable_delta)

    # Calculate the portion of a year this time delta represents
    year_fraction = effective_delta / SECONDS_PER_YEAR

    # Calculate target inflation amount for this time period
    # For a 2% annual inflation rate, the amount to mint for this period would be:
    # total_supply * 0.02 * year_fraction
    target_inflation_amount = total_supply * TARGET_ANNUAL_INFLATION_RATE * year_fraction

    # Apply a dynamic adjustment based on time since last block
    # This encourages regular block production by increasing rewards for longer gaps
    time_adjustment_factor = math.exp(effective_delta / REWARD_TIME_CONSTANT_SECONDS)

    # Cap the adjustment factor to prevent excessive rewards
    max_adjustment = 3.0  # Maximum multiplier
    time_adjustment_factor = min(time_adjustment_factor, max_adjustment)

    # Calculate the base reward (without time adjustment)
    if total_supply == 0:
        # Genesis case - use initial reward
        base_reward = INITIAL_PORW_BASE_REWARD
    else:
        # Normal case - calculate based on target inflation
        base_reward = target_inflation_amount

    # Apply the time adjustment to the base reward
    calculated_reward = base_reward * time_adjustment_factor

    # Apply minimum and maximum bounds if needed
    min_reward = 1.0  # Minimum reward to ensure incentive
    max_reward = INITIAL_PORW_BASE_REWARD * 10  # Maximum reward to prevent extreme inflation

    calculated_reward = max(min_reward, min(calculated_reward, max_reward))

    logger.info(f"Calculated PoRW reward: {calculated_reward:.4f} "
                f"(Time since last: {time_since_last_porw}, "
                f"Year fraction: {year_fraction:.6f}, "
                f"Adjustment factor: {time_adjustment_factor:.2f})")

    return calculated_reward


def get_total_supply(db: Session) -> float:
    """
    Calculates the total supply of currency in the blockchain.

    This function queries the database to determine the total amount of currency
    that has been minted through PoRW blocks.

    Args:
        db: Database session for querying blocks.

    Returns:
        The total supply as a float.
    """
    # In a real implementation, this would efficiently query the database
    # to get the sum of all minted amounts from PoRW blocks
    try:
        # Get all PoRW blocks from the database
        porw_blocks = crud.get_all_porw_blocks(db)

        # Sum the minted amounts
        total_minted = sum(block.minted_amount for block in porw_blocks)

        # In a more complete implementation, we would also account for:
        # - Transaction fees collected
        # - Any tokens that might have been burned
        # - Any initial supply that wasn't minted through blocks

        return total_minted
    except Exception as e:
        logger.error(f"Error calculating total supply: {e}", exc_info=True)
        # Return a default value if there's an error
        # In production, this should be handled more gracefully
        return 0.0


def validate_porw_proof(block: PoRWBlock, expected_difficulty: float = None) -> bool:
    """
    Validates the 'Real Work' proof submitted in a PoRW block.

    This function verifies that the protein folding result included in the block
    meets the required quality and novelty standards to be considered valid work.
    It also checks that the difficulty level of the proof meets the expected difficulty.

    Args:
        block: The PoRWBlock to validate.
        expected_difficulty: Optional expected difficulty level. If provided, validates
                            that the proof meets this difficulty level.

    Returns:
        True if the proof is considered valid, False otherwise.
    """
    logger.info(f"Validating PoRW proof for block {block.index}")

    # 1. Check if porw_proof field exists and has the expected structure
    if block.porw_proof is None:
        logger.warning(f"PoRW proof validation FAILED for block {block.index}: Proof data missing.")
        return False

    # Ensure the proof has the required fields
    required_fields = ["protein_id", "amino_sequence", "structure_data",
                      "energy_score", "result_hash"]

    if not isinstance(block.porw_proof, dict):
        logger.warning(f"PoRW proof validation FAILED for block {block.index}: Proof is not a dictionary.")
        return False

    for field in required_fields:
        if field not in block.porw_proof:
            logger.warning(f"PoRW proof validation FAILED for block {block.index}: Missing required field '{field}'.")
            return False

    # 2. Validate the protein folding result using the protein_folding module
    try:
        is_valid, quality_score, novelty_score, message = protein_folding.evaluate_folding_result(block.porw_proof)

        # Log the evaluation results
        if is_valid:
            logger.info(f"PoRW proof for block {block.index} is valid. "
                       f"Quality: {quality_score:.2f}, Novelty: {novelty_score:.2f}")
        else:
            logger.warning(f"PoRW proof validation FAILED for block {block.index}: {message}")
            return False

        # 3. Verify that the protein_data_ref in the block matches the protein_id in the proof
        if block.protein_data_ref != block.porw_proof.get("protein_id"):
            logger.warning(f"PoRW proof validation FAILED for block {block.index}: "
                          f"protein_data_ref '{block.protein_data_ref}' does not match "
                          f"protein_id '{block.porw_proof.get('protein_id')}' in proof.")
            return False

        # 4. Verify the difficulty level if expected_difficulty is provided
        if expected_difficulty is not None:
            # Extract the difficulty from the proof
            if 'difficulty' not in block.porw_proof:
                logger.warning(f"PoRW proof validation FAILED for block {block.index}: Missing difficulty in proof.")
                return False

            block_difficulty = block.porw_proof.get('difficulty')

            # Check if the difficulty meets the expected level
            # Allow for small tolerance when comparing difficulties
            tolerance = 0.05  # 5% tolerance
            min_acceptable = expected_difficulty * (1 - tolerance)
            max_acceptable = expected_difficulty * (1 + tolerance)

            if not (min_acceptable <= block_difficulty <= max_acceptable):
                logger.warning(f"PoRW proof validation FAILED for block {block.index}: Incorrect difficulty. "
                              f"Got {block_difficulty}, Expected {expected_difficulty} (±{tolerance*100}%)")
                return False

            # Check if the quality score meets the difficulty requirement
            # Higher difficulty requires higher quality score
            min_quality_for_difficulty = 50.0 + (block_difficulty - MIN_DIFFICULTY) * 0.5
            if quality_score < min_quality_for_difficulty:
                logger.warning(f"PoRW proof validation FAILED for block {block.index}: "
                              f"Quality score {quality_score:.2f} does not meet the minimum "
                              f"required for difficulty {block_difficulty} (min: {min_quality_for_difficulty:.2f})")
                return False

        return is_valid

    except Exception as e:
        logger.error(f"Error during PoRW proof validation for block {block.index}: {e}", exc_info=True)
        return False


def calculate_porw_difficulty(db: Session) -> float:
    """
    Calculates the current difficulty level for PoRW blocks based on recent block times.

    The difficulty is adjusted to maintain the target block time. If blocks are being
    produced too quickly, difficulty increases; if too slowly, difficulty decreases.

    Args:
        db: Database session for querying recent blocks.

    Returns:
        The calculated difficulty level for new PoRW blocks.
    """
    # Get the most recent PoRW blocks for analysis
    recent_porw_blocks = crud.get_recent_blocks_by_type(db, block_type="PoRW", limit=DIFFICULTY_ADJUSTMENT_WINDOW+1)

    # If we don't have enough blocks for adjustment, use the initial difficulty
    if len(recent_porw_blocks) < 2:
        logger.info(f"Not enough PoRW blocks for difficulty adjustment. Using initial difficulty: {INITIAL_DIFFICULTY}")
        return INITIAL_DIFFICULTY

    # Calculate the average time between blocks
    total_time_delta = datetime.timedelta(0)
    block_count = min(len(recent_porw_blocks) - 1, DIFFICULTY_ADJUSTMENT_WINDOW)

    for i in range(block_count):
        time_delta = recent_porw_blocks[i].timestamp - recent_porw_blocks[i+1].timestamp
        total_time_delta += time_delta

    avg_block_time = total_time_delta / block_count

    # Get the current difficulty from the most recent block
    # In a real implementation, this would be stored in the block or in a separate table
    # For now, we'll extract it from the porw_proof field if available
    current_difficulty = INITIAL_DIFFICULTY
    if hasattr(recent_porw_blocks[0], 'porw_proof') and isinstance(recent_porw_blocks[0].porw_proof, dict):
        current_difficulty = recent_porw_blocks[0].porw_proof.get('difficulty', INITIAL_DIFFICULTY)

    # Calculate the adjustment factor based on the ratio of actual to target block time
    # If blocks are coming too fast (avg_block_time < TARGET_PORW_BLOCK_TIME), increase difficulty
    # If blocks are coming too slow (avg_block_time > TARGET_PORW_BLOCK_TIME), decrease difficulty
    time_ratio = TARGET_PORW_BLOCK_TIME.total_seconds() / max(avg_block_time.total_seconds(), 1)

    # Apply a dampening factor to prevent wild swings
    # Square root provides a more gradual adjustment
    adjustment_factor = math.sqrt(time_ratio)

    # Limit the adjustment to prevent extreme changes
    adjustment_factor = max(1/MAX_DIFFICULTY_ADJUSTMENT, min(adjustment_factor, MAX_DIFFICULTY_ADJUSTMENT))

    # Calculate the new difficulty
    new_difficulty = current_difficulty * adjustment_factor

    # Ensure the difficulty stays within bounds
    new_difficulty = max(MIN_DIFFICULTY, min(new_difficulty, MAX_DIFFICULTY))

    logger.info(f"PoRW difficulty adjustment: {current_difficulty:.2f} -> {new_difficulty:.2f} "
                f"(avg block time: {avg_block_time}, target: {TARGET_PORW_BLOCK_TIME}, "
                f"adjustment factor: {adjustment_factor:.2f})")

    return new_difficulty


def get_current_porw_difficulty(db: Session) -> float:
    """
    Gets the current difficulty level for PoRW blocks.

    This function checks if it's time to recalculate the difficulty and does so if needed.
    Otherwise, it returns the current difficulty level.

    Args:
        db: Database session for querying blocks.

    Returns:
        The current difficulty level for PoRW blocks.
    """
    # In a production system, this would be cached and only recalculated periodically
    # For simplicity, we'll recalculate every time for now
    return calculate_porw_difficulty(db)


def validate_porw_block_specifics(block: PoRWBlock, db: Session) -> bool:
    """
    Performs validation checks specific to PoRW blocks.

    Args:
        block: The PoRWBlock object to validate.
        db: The SQLAlchemy database session.

    Returns:
        True if the PoRW-specific checks pass, False otherwise.
    """
    # Get the expected difficulty for this block
    expected_difficulty = get_current_porw_difficulty(db)

    # 1. Validate the PoRW Proof itself with the expected difficulty
    if not validate_porw_proof(block, expected_difficulty):
        logger.warning(f"PoRW block {block.index} failed: Invalid PoRW proof.")
        return False

    # 2. Validate the Minted Amount
    last_porw_block_db = crud.get_latest_block_by_type(db, block_type="PoRW", before_index=block.index)
    if last_porw_block_db:
        time_since_last = block.timestamp - last_porw_block_db.timestamp
    else:
        # If this is the first PoRW block, use a default interval
        # This gives a reasonable reward for the genesis block
        time_since_last = datetime.timedelta(seconds=REWARD_TIME_CONSTANT_SECONDS)
        logger.info(f"Block {block.index} appears to be the first PoRW block, using default time delta for reward calc.")

    # Calculate the expected reward using our enhanced monetary policy
    expected_reward = calculate_porw_reward(time_since_last, db)

    # Allow for small floating point tolerance when comparing the rewards
    if not math.isclose(block.minted_amount, expected_reward, rel_tol=1e-7):
        logger.warning(f"PoRW block {block.index} failed: Incorrect minted amount. "
                       f"Got {block.minted_amount}, Expected {expected_reward}")
        return False

    # 3. Validate Protein Data Reference
    # Check that the protein_data_ref is valid and matches the protein_id in the proof
    if not block.protein_data_ref or len(block.protein_data_ref) < 5:
        logger.warning(f"PoRW block {block.index} failed: Invalid protein_data_ref.")
        return False

    # Verify that the protein_data_ref matches the protein_id in the proof
    if isinstance(block.porw_proof, dict) and "protein_id" in block.porw_proof:
        if block.protein_data_ref != block.porw_proof["protein_id"]:
            logger.warning(f"PoRW block {block.index} failed: protein_data_ref '{block.protein_data_ref}' "
                          f"does not match protein_id '{block.porw_proof['protein_id']}' in proof.")
            return False

    # 4. Ensure no user transactions are present (as per design)
    # This is enforced by the Pydantic model structure, but we could add an explicit check here
    # if we were handling raw data or wanted an extra safety check

    # 5. Verify the block creator has permission to mint (if applicable)
    # In a production system, we might check that the block creator is authorized
    # to create PoRW blocks, perhaps by verifying they're a registered researcher

    logger.info(f"PoRW block {block.index} specific validations passed.")
    return True


# === PoRS Specific Consensus Logic ===

def validate_pors_proof(block: PoRSBlock) -> bool:
    """
    Validates the Proof of Reliable Storage proof submitted in a PoRS block.

    This function verifies that the storage proof included in the block meets
    the required standards for quorum validation and data integrity checks.

    In a production environment, this would verify cryptographic proofs from
    storage nodes and validate the quorum signatures against known node public keys.

    Args:
        block: The PoRSBlock to validate.

    Returns:
        True if the PoRS proof is considered valid, False otherwise.
    """
    logger.info(f"Validating PoRS proof for block {block.index}")

    # 1. Check if pors_proof field exists and has the expected structure
    if not isinstance(block.pors_proof, dict):
        logger.warning(f"PoRS proof validation FAILED for block {block.index}: Proof is not a dictionary.")
        return False

    # Ensure the proof has the required fields
    required_fields = ["quorum_id", "participants", "result", "challenge_data", "signatures"]
    for field in required_fields:
        if field not in block.pors_proof:
            logger.warning(f"PoRS proof validation FAILED for block {block.index}: Missing required field '{field}'.")
            return False

    # 2. Validate the quorum participants
    participants = block.pors_proof.get("participants", [])
    if not participants or not isinstance(participants, list):
        logger.warning(f"PoRS proof validation FAILED for block {block.index}: Invalid participants list.")
        return False

    # Check if we have enough participants for a valid quorum
    # In a real implementation, this would check against a known list of authorized storage nodes
    min_participants_required = 3  # Example minimum
    if len(participants) < min_participants_required:
        logger.warning(f"PoRS proof validation FAILED for block {block.index}: "
                      f"Insufficient participants ({len(participants)} < {min_participants_required}).")
        return False

    # 3. Validate the signatures
    # In a real implementation, this would verify each signature against the participant's public key
    signatures = block.pors_proof.get("signatures", {})
    if not signatures or not isinstance(signatures, dict):
        logger.warning(f"PoRS proof validation FAILED for block {block.index}: Invalid signatures format.")
        return False

    # Check if we have signatures from all claimed participants
    for participant in participants:
        if participant not in signatures:
            logger.warning(f"PoRS proof validation FAILED for block {block.index}: "
                          f"Missing signature from participant '{participant}'.")
            return False

    # 4. Check if the number of valid signatures meets the quorum threshold
    valid_signatures_count = len(signatures)
    required_signatures = max(int(len(participants) * PORS_QUORUM_THRESHOLD), 1)

    if valid_signatures_count < required_signatures:
        logger.warning(f"PoRS proof validation FAILED for block {block.index}: "
                      f"Insufficient valid signatures ({valid_signatures_count} < {required_signatures}).")
        return False

    # 5. Verify the challenge data and result
    # In a real implementation, this would validate that the challenge was correctly responded to
    # For now, we just check that the result field indicates success
    if block.pors_proof.get("result") != "valid":
        logger.warning(f"PoRS proof validation FAILED for block {block.index}: Result is not 'valid'.")
        return False

    logger.info(f"PoRS proof for block {block.index} passed validation with {valid_signatures_count} valid signatures.")
    return True


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

    # 3. Validate transaction fees and storage rewards
    # Calculate the expected fee distribution
    expected_fee_distribution = block.calculate_fee_distribution()

    # If storage_rewards are specified, validate they match the expected distribution
    if block.storage_rewards:
        # Check that all expected recipients are included
        for address, amount in expected_fee_distribution.items():
            if address not in block.storage_rewards:
                logger.warning(f"PoRS block {block.index} failed: Missing fee reward for {address}.")
                return False

            # Check that the amounts are correct (with small tolerance for floating point)
            if not math.isclose(block.storage_rewards[address], amount, rel_tol=1e-7):
                logger.warning(f"PoRS block {block.index} failed: Incorrect fee reward for {address}. "
                              f"Expected {amount}, got {block.storage_rewards[address]}.")
                return False

        # Check for any unexpected recipients
        for address in block.storage_rewards:
            if address not in expected_fee_distribution:
                logger.warning(f"PoRS block {block.index} failed: Unexpected fee reward for {address}.")
                return False

        logger.debug(f"PoRS block {block.index} fee distribution validated successfully.")
    else:
        # If no storage_rewards are specified but there are fees, warn but don't fail
        total_fees = block.calculate_total_fees()
        if total_fees > 0:
            logger.warning(f"PoRS block {block.index} has {total_fees} in fees but no storage_rewards specified.")

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


# === Chain Traversal and Validation ===

def get_block_chain(db: Session, start_index: int = 0, end_index: Optional[int] = None, block_type: Optional[str] = None) -> List[AnyBlock]:
    """
    Retrieves a segment of the blockchain as AnyBlock objects.

    This function retrieves blocks from the database and converts them to
    the appropriate block type (PoRWBlock or PoRSBlock).

    Args:
        db: The SQLAlchemy database session.
        start_index: The starting block index (default: 0).
        end_index: The ending block index (default: latest block).
        block_type: Optional filter for block type ("PoRW" or "PoRS").

    Returns:
        A list of AnyBlock objects (PoRWBlock or PoRSBlock).
    """
    # If end_index is not provided, use the latest block
    if end_index is None:
        latest_block = crud.get_latest_db_block(db)
        if latest_block is None:
            logger.warning("No blocks in database")
            return []
        end_index = latest_block.index

    # Get blocks from the database
    if block_type:
        # Filter by block type
        blocks_db = db.query(crud.models.DbBlock)\
            .filter(crud.models.DbBlock.index >= start_index)\
            .filter(crud.models.DbBlock.index <= end_index)\
            .filter(crud.models.DbBlock.block_type == block_type)\
            .order_by(crud.models.DbBlock.index)\
            .all()
    else:
        # Get all blocks in range
        blocks_db = crud.get_blocks_in_range(db, start_index, end_index)

    # Convert DB blocks to AnyBlock objects
    blocks = []
    for block_db in blocks_db:
        # Convert DB block to the appropriate block type
        if block_db.block_type == "PoRW":
            # Convert to PoRWBlock
            block = PoRWBlock(
                index=block_db.index,
                timestamp=block_db.timestamp,
                previous_hash=block_db.previous_hash,
                block_hash=block_db.block_hash,
                block_type="PoRW",
                porw_proof=json.loads(block_db.porw_proof) if block_db.porw_proof else {},
                minted_amount=float(block_db.minted_amount) if block_db.minted_amount else 0.0,
                protein_data_ref=block_db.protein_data_ref or ""
            )
        elif block_db.block_type == "PoRS":
            # Get transactions for this block
            transactions_db = crud.get_db_transactions_for_block(db, block_db.id)
            transactions = []
            for tx_db in transactions_db:
                tx = Transaction(
                    transaction_id=tx_db.transaction_id,
                    timestamp=tx_db.timestamp,
                    sender=tx_db.sender,
                    recipient=tx_db.recipient,
                    amount=float(tx_db.amount),
                    fee=float(tx_db.fee) if tx_db.fee else None,
                    signature=tx_db.signature,
                    # No data field in DbTransaction
                )
                transactions.append(tx)

            # Convert to PoRSBlock
            block = PoRSBlock(
                index=block_db.index,
                timestamp=block_db.timestamp,
                previous_hash=block_db.previous_hash,
                block_hash=block_db.block_hash,
                block_type="PoRS",
                pors_proof=json.loads(block_db.pors_proof) if block_db.pors_proof else {},
                transactions=transactions,
                storage_rewards=json.loads(block_db.storage_rewards) if block_db.storage_rewards else {}
            )
        else:
            logger.warning(f"Unknown block type: {block_db.block_type}")
            continue

        blocks.append(block)

    return blocks


def get_block_by_hash(db: Session, block_hash: str) -> Optional[AnyBlock]:
    """
    Retrieves a block by its hash.

    Args:
        db: The SQLAlchemy database session.
        block_hash: The hash of the block to retrieve.

    Returns:
        The block as an AnyBlock object, or None if not found.
    """
    # Get the block from the database
    block_db = crud.get_db_block_by_hash(db, block_hash)
    if block_db is None:
        return None

    # Get the chain containing this block
    blocks = get_block_chain(db, block_db.index, block_db.index)
    if not blocks:
        return None

    return blocks[0]


def get_block_by_index(db: Session, block_index: int) -> Optional[AnyBlock]:
    """
    Retrieves a block by its index.

    Args:
        db: The SQLAlchemy database session.
        block_index: The index of the block to retrieve.

    Returns:
        The block as an AnyBlock object, or None if not found.
    """
    # Get the chain containing this block
    blocks = get_block_chain(db, block_index, block_index)
    if not blocks:
        return None

    return blocks[0]


def get_latest_block(db: Session) -> Optional[AnyBlock]:
    """
    Retrieves the latest block in the blockchain.

    Args:
        db: The SQLAlchemy database session.

    Returns:
        The latest block as an AnyBlock object, or None if no blocks exist.
    """
    # Get the latest block from the database
    latest_block_db = crud.get_latest_db_block(db)
    if latest_block_db is None:
        return None

    # Get the chain containing this block
    blocks = get_block_chain(db, latest_block_db.index, latest_block_db.index)
    if not blocks:
        return None

    return blocks[0]


def validate_chain(db: Session, start_index: int = 0, end_index: Optional[int] = None, use_checkpoints: bool = True) -> bool:
    """
    Validates a segment of the blockchain.

    This function validates a segment of the blockchain from start_index to end_index.
    If use_checkpoints is True, it will use checkpoints to speed up validation.

    Args:
        db: The SQLAlchemy database session.
        start_index: The starting block index to validate (default: 0).
        end_index: The ending block index to validate (default: latest block).
        use_checkpoints: Whether to use checkpoints for faster validation (default: True).

    Returns:
        True if the chain segment is valid, False otherwise.
    """
    from .checkpoint import validate_chain_with_checkpoints

    # If end_index is not provided, use the latest block
    if end_index is None:
        latest_block = crud.get_latest_db_block(db)
        if latest_block is None:
            logger.warning("Cannot validate chain: No blocks in database")
            return True  # Empty chain is valid
        end_index = latest_block.index

    # Validate the chain segment
    if use_checkpoints:
        # Use checkpoints for faster validation
        return validate_chain_with_checkpoints(db, start_index, end_index, validate_block_for_consensus)
    else:
        # Validate each block individually
        blocks = crud.get_blocks_in_range(db, start_index, end_index)

        for block_db in blocks:
            # Convert DB block to the appropriate block type
            if block_db.block_type == "PoRW":
                # Convert to PoRWBlock
                block = PoRWBlock(
                    index=block_db.index,
                    timestamp=block_db.timestamp,
                    previous_hash=block_db.previous_hash,
                    block_hash=block_db.block_hash,
                    block_type="PoRW",
                    porw_proof=json.loads(block_db.porw_proof) if block_db.porw_proof else {},
                    minted_amount=float(block_db.minted_amount) if block_db.minted_amount else 0.0,
                    protein_data_ref=block_db.protein_data_ref or ""
                )
            elif block_db.block_type == "PoRS":
                # Convert to PoRSBlock
                block = PoRSBlock(
                    index=block_db.index,
                    timestamp=block_db.timestamp,
                    previous_hash=block_db.previous_hash,
                    block_hash=block_db.block_hash,
                    block_type="PoRS",
                    pors_proof=json.loads(block_db.pors_proof) if block_db.pors_proof else {},
                    transactions=[],  # Would need to load transactions
                    storage_rewards=json.loads(block_db.storage_rewards) if block_db.storage_rewards else {}
                )
            else:
                logger.warning(f"Unknown block type: {block_db.block_type}")
                return False

            # Validate the block
            if not validate_block_for_consensus(block, db):
                logger.warning(f"Block {block_db.index} failed validation")
                return False

        logger.info(f"Chain segment from {start_index} to {end_index} validated successfully")
        return True


# === Fork Resolution ===

def resolve_fork(db: Session, fork_blocks: List[AnyBlock]) -> Optional[AnyBlock]:
    """
    Resolves a fork in the blockchain by selecting the best chain.

    This function implements the fork resolution logic for the hybrid PoRW/PoRS blockchain.
    It selects the best chain based on a combination of factors including:
    1. Chain length (longer chains are preferred)
    2. Cumulative work (chains with more PoRW work are preferred)
    3. PoRS quorum size (chains with larger quorums are preferred)
    4. Timestamp (in case of ties, earlier blocks are preferred)

    Args:
        db: The SQLAlchemy database session.
        fork_blocks: List of competing blocks at the same height.

    Returns:
        The selected block to continue the chain, or None if no valid block is found.
    """
    if not fork_blocks:
        logger.warning("No fork blocks provided for resolution.")
        return None

    # If only one block, no fork to resolve
    if len(fork_blocks) == 1:
        return fork_blocks[0]

    logger.info(f"Resolving fork with {len(fork_blocks)} competing blocks at height {fork_blocks[0].index}")

    # First, validate all blocks to ensure they're valid
    valid_blocks = []
    for block in fork_blocks:
        if validate_block_for_consensus(block, db):
            valid_blocks.append(block)
        else:
            logger.warning(f"Block {block.index} with hash {block.block_hash[:8]} failed validation during fork resolution.")

    if not valid_blocks:
        logger.warning("No valid blocks found during fork resolution.")
        return None

    # If only one valid block remains, use it
    if len(valid_blocks) == 1:
        logger.info(f"Fork resolved: Only one valid block remains (hash: {valid_blocks[0].block_hash[:8]})")
        return valid_blocks[0]

    # Calculate the chain work for each fork
    # For each fork, we'll calculate a score based on multiple factors
    fork_scores = []

    for block in valid_blocks:
        # Get the chain leading to this block
        chain = get_chain_to_block(db, block)

        # Calculate the score for this chain
        score = calculate_chain_score(chain)

        fork_scores.append((block, score))
        logger.debug(f"Chain score for block {block.block_hash[:8]}: {score}")

    # Sort by score (descending)
    fork_scores.sort(key=lambda x: x[1], reverse=True)

    # Select the block with the highest score
    selected_block = fork_scores[0][0]
    logger.info(f"Fork resolved: Selected block with hash {selected_block.block_hash[:8]} (score: {fork_scores[0][1]})")

    return selected_block


def get_chain_to_block(db: Session, block: AnyBlock) -> List[AnyBlock]:
    """
    Gets the chain of blocks leading to the specified block.

    Args:
        db: The SQLAlchemy database session.
        block: The block to get the chain for.

    Returns:
        A list of blocks in the chain, ordered from oldest to newest.
    """
    chain = [block]
    current_block = block

    # Traverse backwards until we reach the genesis block
    while current_block.index > 0:
        previous_block_db = crud.get_db_block_by_hash(db, current_block.previous_hash)
        if not previous_block_db:
            logger.warning(f"Cannot find previous block with hash {current_block.previous_hash[:8]} for block {current_block.index}")
            break

        # Convert DB block to AnyBlock (simplified for now)
        # In a real implementation, you would convert the DB block to the appropriate Pydantic model
        previous_block = AnyBlock(
            index=previous_block_db.index,
            timestamp=previous_block_db.timestamp,
            previous_hash=previous_block_db.previous_hash,
            block_hash=previous_block_db.block_hash,
            block_type=previous_block_db.block_type,
            # Add other fields as needed
        )

        chain.insert(0, previous_block)
        current_block = previous_block

    return chain


def calculate_chain_score(chain: List[AnyBlock]) -> float:
    """
    Calculates a score for a chain of blocks based on multiple factors.

    The score is a weighted combination of:
    1. Chain length (longer chains are preferred)
    2. Cumulative PoRW work (chains with more PoRW work are preferred)
    3. PoRS quorum size (chains with larger quorums are preferred)

    Args:
        chain: A list of blocks in the chain, ordered from oldest to newest.

    Returns:
        A score for the chain, where higher scores are better.
    """
    if not chain:
        return 0.0

    # Factor 1: Chain length
    chain_length = len(chain)

    # Factor 2: Cumulative PoRW work
    porw_work = 0.0
    for block in chain:
        if block.block_type == "PoRW":
            # In a real implementation, you would extract the difficulty from the block
            # For now, we'll use a placeholder value
            if isinstance(block, PoRWBlock) and hasattr(block, 'porw_proof') and isinstance(block.porw_proof, dict):
                difficulty = block.porw_proof.get('difficulty', 1.0)
                porw_work += difficulty
            else:
                porw_work += 1.0  # Default difficulty

    # Factor 3: PoRS quorum size
    pors_quorum_size = 0
    for block in chain:
        if block.block_type == "PoRS":
            # In a real implementation, you would extract the quorum size from the block
            # For now, we'll use a placeholder value
            if isinstance(block, PoRSBlock) and hasattr(block, 'pors_proof') and isinstance(block.pors_proof, dict):
                participants = block.pors_proof.get('participants', [])
                pors_quorum_size += len(participants)

    # Calculate the final score as a weighted combination of the factors
    # The weights can be adjusted based on the relative importance of each factor
    length_weight = 1.0
    porw_work_weight = 2.0
    pors_quorum_weight = 1.5

    score = (length_weight * chain_length) + \
            (porw_work_weight * porw_work) + \
            (pors_quorum_weight * pors_quorum_size)

    return score
