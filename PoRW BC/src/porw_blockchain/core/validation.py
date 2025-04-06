# src/porw_blockchain/core/validation.py
"""
Core validation functions for blockchain structures, including hashing.
"""

import hashlib
import json
import datetime
from typing import Any, Dict, List # For type hinting block data

# Import the Pydantic model for Block
from .structures import Block, Transaction


def ComplexEncoder(obj: Any) -> Any:
    """Custom JSON encoder to handle datetime objects and Pydantic models."""
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, Transaction): # Assuming Transaction is Pydantic
        # Use Pydantic's recommended way to get dict representation
        return obj.model_dump(mode='json')
    # Add handling for other custom types if necessary
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def calculate_block_hash(
    index: int,
    timestamp: datetime.datetime,
    transactions: List[Transaction],
    proof: int,
    previous_hash: str,
) -> str:
    """
    Calculates the SHA256 hash of the essential block data.

    Args:
        index: The block's index.
        timestamp: The block's timestamp.
        transactions: The list of transactions within the block.
        proof: The block's proof/nonce value.
        previous_hash: The hash of the previous block.

    Returns:
        The calculated SHA256 hash as a hexadecimal string.
    """
    block_data: Dict[str, Any] = {
        "index": index,
        "timestamp": timestamp,
        # Ensure transactions are consistently represented
        "transactions": [t.model_dump(mode='json') for t in transactions],
        "proof": proof,
        "previous_hash": previous_hash,
    }

    # Encode the dictionary to a JSON string with sorted keys for consistency
    # Use the custom encoder for datetime and Transaction objects
    block_string = json.dumps(block_data, sort_keys=True, default=ComplexEncoder)

    # Calculate the SHA256 hash
    return hashlib.sha256(block_string.encode()).hexdigest()


def validate_block_hash(block: Block) -> bool:
    """
    Validates if the block's stored hash matches its calculated hash.

    Note: Assumes block.hash is already set. The hash is calculated
    based on all other relevant fields.

    Args:
        block: The Block object to validate.

    Returns:
        True if the hash is valid, False otherwise.
    """
    if block.hash is None:
        return False # Cannot validate if hash isn't set

    calculated_hash = calculate_block_hash(
        index=block.index,
        timestamp=block.timestamp,
        transactions=block.transactions,
        proof=block.proof,
        previous_hash=block.previous_hash,
    )
    return block.hash == calculated_hash


# Note: Basic structure validation (field existence, types) is largely handled
# by Pydantic upon Block object creation or parsing.
# Additional validation functions (e.g., validate_proof_of_work,
# validate_chain_linkage) will be added later, likely in consensus.py.