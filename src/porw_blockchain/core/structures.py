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
    fee: Optional[float] = Field(None, ge=0, description="Transaction fee paid to validators (optional, defaults to standard fee if None).")
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    signature: Optional[str] = Field(None, description="Digital signature of the transaction data by the sender.")
    # Unique identifier for the transaction
    transaction_id: Optional[str] = Field(None, description="Unique hash identifier for this transaction.")
    # Optional memo field for additional information
    memo: Optional[str] = Field(None, description="Optional memo for additional information (can be encrypted).")
    # Flag indicating whether the memo is encrypted
    is_memo_encrypted: bool = Field(False, description="Flag indicating whether the memo is encrypted.")
    # Confidential transaction data
    confidential_data: Optional[Dict[str, Any]] = Field(None, description="Data for confidential transactions (commitments, range proofs, etc.).")
    # Flag indicating whether this is a confidential transaction
    is_confidential: bool = Field(False, description="Flag indicating whether this is a confidential transaction.")
    # Stealth transaction metadata
    stealth_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata for stealth transactions.")
    # Flag indicating whether this is a stealth transaction
    is_stealth: bool = Field(False, description="Flag indicating whether this is a stealth transaction.")

    # Automatically generate transaction_id if not provided
    @validator('transaction_id', pre=True, always=True)
    def set_transaction_id(cls, v, values):
        if v is None:
            # Create a stable representation for hashing
            tx_data = {
                "sender": values.get('sender'),
                "recipient": values.get('recipient'),
                "amount": values.get('amount'),
                "fee": values.get('fee'),  # Include fee in hash calculation
                # Use isoformat for consistent timestamp representation
                "timestamp": values.get('timestamp').isoformat()
            }

            # Include memo if present
            memo = values.get('memo')
            if memo is not None:
                tx_data["memo"] = memo
                tx_data["is_memo_encrypted"] = values.get('is_memo_encrypted', False)

            # Include confidential transaction data if present
            is_confidential = values.get('is_confidential', False)
            confidential_data = values.get('confidential_data')
            if is_confidential and confidential_data is not None:
                tx_data["is_confidential"] = is_confidential
                tx_data["confidential_data"] = confidential_data

            # Include stealth transaction metadata if present
            is_stealth = values.get('is_stealth', False)
            stealth_metadata = values.get('stealth_metadata')
            if is_stealth and stealth_metadata is not None:
                tx_data["is_stealth"] = is_stealth
                tx_data["stealth_metadata"] = stealth_metadata

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
            "fee": self.fee,  # Include fee in signing data
            "timestamp": self.timestamp.isoformat(), # Consistent format
        }

        # Include memo if present
        if self.memo is not None:
            signing_data["memo"] = self.memo
            signing_data["is_memo_encrypted"] = self.is_memo_encrypted

        # Include confidential transaction data if present
        if self.is_confidential and self.confidential_data is not None:
            signing_data["is_confidential"] = self.is_confidential
            signing_data["confidential_data"] = self.confidential_data

        # Include stealth transaction metadata if present
        if self.is_stealth and self.stealth_metadata is not None:
            signing_data["is_stealth"] = self.is_stealth
            signing_data["stealth_metadata"] = self.stealth_metadata

        # Use separators=(',', ':') for compact, deterministic JSON
        return json.dumps(signing_data, sort_keys=True, separators=(',', ':')).encode('utf-8')

    def calculate_standard_fee(self) -> float:
        """
        Calculates the standard transaction fee based on the transaction amount.

        The standard fee is calculated as a percentage of the transaction amount,
        with minimum and maximum bounds to ensure fairness.

        Returns:
            The calculated standard fee.
        """
        # Define fee parameters
        BASE_FEE_PERCENTAGE = 0.001  # 0.1% of transaction amount
        MIN_FEE = 0.01  # Minimum fee to prevent dust transactions
        MAX_FEE = 10.0  # Maximum fee to prevent excessive costs for large transactions

        # Calculate fee as a percentage of the transaction amount
        calculated_fee = self.amount * BASE_FEE_PERCENTAGE

        # Apply minimum and maximum bounds
        fee = max(MIN_FEE, min(calculated_fee, MAX_FEE))

        return fee

    def get_effective_fee(self) -> float:
        """
        Returns the effective fee for this transaction.

        If a fee was explicitly set, that value is used.
        Otherwise, the standard fee is calculated and returned.

        Returns:
            The effective transaction fee.
        """
        if self.fee is not None:
            return self.fee
        return self.calculate_standard_fee()

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
    # Rewards specifically for storage providers/validators in this block
    storage_rewards: Optional[Dict[str, float]] = Field(None, description="Mapping of node addresses to storage rewards earned in this block.")
    # Block creator who gets a portion of the transaction fees
    creator_address: Optional[str] = Field(None, description="Address of the node that created this block.")
    # Fee distribution parameters
    creator_fee_percentage: float = Field(0.3, ge=0, le=1, description="Percentage of transaction fees that go to the block creator (0-1).")

    def calculate_total_fees(self) -> float:
        """
        Calculates the total transaction fees in this block.

        Returns:
            The sum of all transaction fees in the block.
        """
        return sum(tx.get_effective_fee() for tx in self.transactions)

    def calculate_fee_distribution(self) -> Dict[str, float]:
        """
        Calculates how transaction fees should be distributed among participants.

        The block creator receives a percentage of the fees, and the rest is
        distributed among storage providers based on their participation.

        Returns:
            A dictionary mapping participant addresses to their fee rewards.
        """
        total_fees = self.calculate_total_fees()
        fee_distribution = {}

        # If there are no fees, return an empty distribution
        if total_fees <= 0:
            return fee_distribution

        # Allocate creator's portion if a creator is specified
        creator_portion = total_fees * self.creator_fee_percentage
        if self.creator_address:
            fee_distribution[self.creator_address] = creator_portion

        # Distribute the remaining fees among storage providers
        remaining_fees = total_fees - creator_portion

        # Get the list of storage providers from the PoRS proof
        storage_providers = self.pors_proof.get("participants", [])
        if not storage_providers:
            # If no storage providers, give remaining fees to creator or discard
            if self.creator_address:
                fee_distribution[self.creator_address] += remaining_fees
            return fee_distribution

        # Distribute remaining fees equally among storage providers
        fee_per_provider = remaining_fees / len(storage_providers)
        for provider in storage_providers:
            if provider in fee_distribution:
                fee_distribution[provider] += fee_per_provider
            else:
                fee_distribution[provider] = fee_per_provider

        return fee_distribution

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

