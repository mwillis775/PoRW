# src/porw_blockchain/core/structures.py
"""
Pydantic models defining the core data structures for the PoRW/PoRS blockchain.

Includes models for Transactions, and distinct block types for Proof of Real Work (PoRW)
and Proof of Reliable Storage (PoRS).
"""

import datetime
import hashlib
import json
from typing import List, Optional, Literal, Any, Dict, Union
from pydantic import BaseModel, Field, validator, computed_field

# --- Transaction Structure ---

class Transaction(BaseModel):
    """
    Represents a standard transaction transferring value between addresses.
    These are typically included in PoRS blocks.
    """
    sender: str = Field(..., description="Address of the sender.")
    recipient: str = Field(..., description="Address of the recipient.")
    amount: float = Field(..., gt=0, description="Amount of currency transferred (must be positive).")
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    signature: Optional[str] = Field(None, description="Digital signature of the transaction data by the sender.")
    # Unique identifier for the transaction
    transaction_id: Optional[str] = Field(None, description="Unique hash identifier for this transaction.")

    # Automatically generate transaction_id if not provided
    @validator('transaction_id', pre=True, always=True)
    def set_transaction_id(cls, v, values):
        if v is None:
            # Create a stable representation for hashing
            tx_data = {
                "sender": values.get('sender'),
                "recipient": values.get('recipient'),
                "amount": values.get('amount'),
                # Use isoformat for consistent timestamp representation
                "timestamp": values.get('timestamp').isoformat()
            }
            tx_string = json.dumps(tx_data, sort_keys=True)
            return hashlib.sha256(tx_string.encode()).hexdigest()
        return v

    def get_signing_data(self) -> bytes:
        """
        Returns the transaction data in a consistent format for signing/verification.
        Excludes the signature itself and the transaction_id (which depends on other fields).
        """
        signing_data = {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp.isoformat(), # Consistent format
        }
        # Use separators=(',', ':') for compact, deterministic JSON
        return json.dumps(signing_data, sort_keys=True, separators=(',', ':')).encode('utf-8')

    class Config:
        # Allow ORM mode if needed later for SQLAlchemy integration
        from_attributes = True


# --- Base Block Structure ---

class BlockBase(BaseModel):
    """
    Base model containing fields common to all block types.
    """
    index: int = Field(..., ge=0, description="Sequential index of the block in the chain (Genesis = 0).")
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    previous_hash: str = Field(..., description="Hash of the preceding block in the chain.")
    # Hash is computed based on block content, so optional initially
    block_hash: Optional[str] = Field(None, description="SHA256 hash of the block's content.")

    def calculate_hash(self) -> str:
        """Calculates the SHA256 hash of the block's content."""
        # Exclude block_hash itself from the hash calculation
        block_content = self.model_dump(exclude={'block_hash'}, mode='json')
        block_string = json.dumps(block_content, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    @validator('block_hash', pre=True, always=True)
    def set_block_hash(cls, v, values):
        """Sets the block hash if it's not already provided."""
        if v is None:
            # Temporarily create a model instance to call calculate_hash
            # This assumes all other required fields are present in 'values'
            # Note: Pydantic v2 might handle this differently with computed fields
            # Need to be careful about field availability during validation
            temp_model_data = values.copy()
            temp_model_data['block_hash'] = None # Ensure hash is excluded
            # Need to handle potential missing fields if validation runs early
            if all(k in temp_model_data for k in cls.model_fields if k != 'block_hash'):
                 # Create a temporary instance excluding the hash field initially
                 temp_instance_dict = {k: v for k, v in values.items() if k != 'block_hash'}
                 temp_instance = cls(**temp_instance_dict) # Create instance without hash
                 return temp_instance.calculate_hash() # Calculate based on other fields
            else:
                 # Cannot calculate hash yet if fields are missing
                 return None # Or raise an error
        return v

    class Config:
        from_attributes = True
        # Using frozen=True makes the block immutable after creation, which is desirable
        # but might complicate hash calculation/setting. Revisit if needed.
        # frozen = True


# --- PoRW Block Structure ---

class PoRWBlock(BlockBase):
    """
    Represents a Proof of Real Work block, focused on minting new currency
    based on validated scientific computation (e.g., protein folding).
    """
    block_type: Literal["PoRW"] = Field("PoRW", description="Identifies the block type as PoRW.")
    porw_proof: Any = Field(..., description="Proof data specific to the 'Real Work' performed (e.g., protein folding result hash, validation metrics).")
    minted_amount: float = Field(..., gt=0, description="Amount of new currency minted by this block.")
    protein_data_ref: str = Field(..., description="Identifier or reference to the validated protein structure data generated.")
    # PoRW blocks primarily mint currency, they don't typically process user transactions.
    # A 'coinbase' transaction might be implicitly represented by minted_amount.

    class Config:
        json_schema_extra = {
            "example": {
                "index": 101,
                "timestamp": "2025-04-06T12:00:00Z",
                "previous_hash": "a1b2c3d4...",
                "block_type": "PoRW",
                "porw_proof": {"folding_hash": "xyz...", "score": 95.5},
                "minted_amount": 50.0,
                "protein_data_ref": "protein_structure_id_123",
                "block_hash": "e5f6g7h8...",
            }
        }


# --- PoRS Block Structure ---

class PoRSBlock(BlockBase):
    """
    Represents a Proof of Reliable Storage block, focused on processing
    user transactions and ensuring data integrity via storage checks.
    """
    block_type: Literal["PoRS"] = Field("PoRS", description="Identifies the block type as PoRS.")
    pors_proof: Dict[str, Any] = Field(..., description="Proof data specific to the storage validation (e.g., quorum results, challenge/response data).")
    transactions: List[Transaction] = Field(..., description="List of user transactions included in this block.")
    # Optional: Rewards specifically for storage providers/validators in this block
    storage_rewards: Optional[Dict[str, float]] = Field(None, description="Mapping of node addresses to storage rewards earned in this block.")

    class Config:
        json_schema_extra = {
            "example": {
                "index": 102,
                "timestamp": "2025-04-06T12:05:00Z",
                "previous_hash": "e5f6g7h8...", # Hash of the previous PoRW block
                "block_type": "PoRS",
                "pors_proof": {"quorum_id": "q789", "participants": ["nodeA", "nodeB"], "result": "valid"},
                "transactions": [
                    {
                        "sender": "address1...",
                        "recipient": "address2...",
                        "amount": 15.0,
                        "timestamp": "2025-04-06T12:04:00Z",
                        "signature": "sig1...",
                        "transaction_id": "txid1..."
                    },
                     {
                        "sender": "address3...",
                        "recipient": "address4...",
                        "amount": 5.0,
                        "timestamp": "2025-04-06T12:04:30Z",
                        "signature": "sig2...",
                        "transaction_id": "txid2..."
                    }
                ],
                "storage_rewards": {"nodeA": 0.1, "nodeB": 0.1},
                "block_hash": "f9g0h1i2...",
            }
        }


# --- Union Type for Blocks ---

# This allows functions to accept either type of block
AnyBlock = Union[PoRWBlock, PoRSBlock]

